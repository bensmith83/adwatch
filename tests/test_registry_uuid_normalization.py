"""Cross-platform UUID normalization in ParserRegistry.

BLE backends report service UUIDs in different formats:

- bleak / BlueZ (Linux, Android): full 128-bit lowercase, dashed,
  e.g. ``0000fcf1-0000-1000-8000-00805f9b34fb``
- CoreBluetooth (iOS, macOS): short uppercase 16-bit form, e.g. ``FCF1``
- Some backends: short lowercase, e.g. ``fcf1``

Plugins register either form interchangeably. Registry matching must
succeed regardless of which form the OS delivered.
"""

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry


class _Stub:
    def parse(self, raw):
        return None


def _make_ad(**kwargs):
    defaults = dict(
        timestamp="2025-01-15T10:30:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        manufacturer_data=None,
        service_data=None,
        service_uuids=[],
        local_name=None,
        rssi=-60,
        tx_power=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _registry_with(service_uuid):
    registry = ParserRegistry()
    registry.register(
        name="stub",
        service_uuid=service_uuid,
        description="test",
        version="1.0.0",
        core=False,
        instance=_Stub(),
    )
    return registry


# ---------------------------------------------------------------------------
# service_uuids list — all three ad-side formats must match any reg-side form
# ---------------------------------------------------------------------------

class TestServiceUuidsListNormalization:
    def test_registered_short_matches_ad_full_128bit(self):
        """Registered 'fcf1' must match ad carrying the full 128-bit form (Linux/bleak)."""
        registry = _registry_with("fcf1")
        ad = _make_ad(service_uuids=["0000fcf1-0000-1000-8000-00805f9b34fb"])
        assert len(registry.match(ad)) == 1

    def test_registered_short_matches_ad_uppercase_short(self):
        """Registered 'fcf1' must match ad carrying 'FCF1' (iOS CoreBluetooth)."""
        registry = _registry_with("fcf1")
        ad = _make_ad(service_uuids=["FCF1"])
        assert len(registry.match(ad)) == 1

    def test_registered_full_matches_ad_short(self):
        """Registered full form must match ad carrying short form."""
        registry = _registry_with("0000fcf1-0000-1000-8000-00805f9b34fb")
        ad = _make_ad(service_uuids=["fcf1"])
        assert len(registry.match(ad)) == 1

    def test_registered_uppercase_short_matches_ad_lowercase_full(self):
        """Registered 'FCF1' (iOS style) must match ad carrying full lowercase (Linux style)."""
        registry = _registry_with("FCF1")
        ad = _make_ad(service_uuids=["0000fcf1-0000-1000-8000-00805f9b34fb"])
        assert len(registry.match(ad)) == 1

    def test_registered_full_uppercase_matches_ad_full_lowercase(self):
        """Case-insensitive match across full UUIDs."""
        registry = _registry_with("0000FCF1-0000-1000-8000-00805F9B34FB")
        ad = _make_ad(service_uuids=["0000fcf1-0000-1000-8000-00805f9b34fb"])
        assert len(registry.match(ad)) == 1


# ---------------------------------------------------------------------------
# service_data dict — keys arrive in the same format variations
# ---------------------------------------------------------------------------

class TestServiceDataKeyNormalization:
    def test_registered_short_matches_service_data_full_key(self):
        """Service-data keyed by full 128-bit UUID must match short registration."""
        registry = _registry_with("feed")
        ad = _make_ad(
            service_data={
                "0000feed-0000-1000-8000-00805f9b34fb": b"\x02\x00payload",
            }
        )
        assert len(registry.match(ad)) == 1

    def test_registered_short_matches_service_data_uppercase_key(self):
        """Service-data keyed by uppercase short (iOS) must match lowercase registration."""
        registry = _registry_with("feed")
        ad = _make_ad(service_data={"FEED": b"\x02\x00payload"})
        assert len(registry.match(ad)) == 1

    def test_registered_full_matches_service_data_short_key(self):
        """Service-data keyed by short form must match full-form registration."""
        registry = _registry_with("0000feed-0000-1000-8000-00805f9b34fb")
        ad = _make_ad(service_data={"feed": b"\x02\x00payload"})
        assert len(registry.match(ad)) == 1


# ---------------------------------------------------------------------------
# List-of-uuids registration — each entry normalized independently
# ---------------------------------------------------------------------------

class TestListRegistrationNormalization:
    def test_list_with_mixed_forms_matches_any_ad_form(self):
        registry = ParserRegistry()
        registry.register(
            name="stub",
            service_uuid=["fe78", "0000febe-0000-1000-8000-00805f9b34fb"],
            description="test",
            version="1.0.0",
            core=False,
            instance=_Stub(),
        )
        ad_short = _make_ad(service_uuids=["febe"])
        ad_full = _make_ad(service_uuids=["0000fe78-0000-1000-8000-00805f9b34fb"])
        ad_upper = _make_ad(service_uuids=["FE78"])
        assert len(registry.match(ad_short)) == 1
        assert len(registry.match(ad_full)) == 1
        assert len(registry.match(ad_upper)) == 1


# ---------------------------------------------------------------------------
# Negative cases — non-matching UUIDs must still not match
# ---------------------------------------------------------------------------

class TestNoFalsePositives:
    def test_different_short_uuid_does_not_match(self):
        registry = _registry_with("fcf1")
        ad = _make_ad(service_uuids=["0000fcf2-0000-1000-8000-00805f9b34fb"])
        assert len(registry.match(ad)) == 0

    def test_custom_128bit_uuid_does_not_match_sig_form(self):
        """A non-SIG 128-bit UUID must not be collapsed to a short form."""
        registry = _registry_with("fcf1")
        ad = _make_ad(service_uuids=["12345678-1234-1234-1234-123456789abc"])
        assert len(registry.match(ad)) == 0

    def test_different_non_sig_128bit_uuids_do_not_match(self):
        registry = _registry_with("12345678-1234-1234-1234-123456789abc")
        ad = _make_ad(service_uuids=["87654321-1234-1234-1234-123456789abc"])
        assert len(registry.match(ad)) == 0
