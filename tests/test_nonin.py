"""Tests for the Nonin pulse-oximeter plugin.

Per apk-ble-hunting/reports/medixine-nonin-devicehub_passive.md: the Medixine
Device Hub scans by MAC only, so the passive discriminators are the Nonin
proprietary service UUID (Nonin OUI 00:02:A5 in the tail) and the
`Nonin_3150` / `Nonin_3230` model name. SIG PLX 0x1822 is vendor-agnostic and
must never match on its own.
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.nonin import (
    NoninParser,
    NONIN_SERVICE_UUID,
    SIG_PLX_SERVICE_UUID,
    NONIN_MODELS,
)


def _make_ad(**kwargs):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "00:1C:05:11:22:33",
        "address_type": "public",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(
        name="nonin",
        service_uuid=NONIN_SERVICE_UUID,
        local_name_pattern=r"(?i)^nonin[ _-]?\d{3,4}",
        description="Nonin",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(NoninParser):
        pass

    return _P


class TestNoninConstants:
    def test_proprietary_uuid(self):
        assert NONIN_SERVICE_UUID == "46a970e0-0d5f-11e2-8b5e-0002a5d5c51b"

    def test_uuid_carries_nonin_oui_tail(self):
        assert NONIN_SERVICE_UUID.endswith("0002a5d5c51b")

    def test_sig_plx_uuid(self):
        assert SIG_PLX_SERVICE_UUID == "1822"

    def test_known_models(self):
        assert NONIN_MODELS["3150"] == "WristOx2 3150"
        assert NONIN_MODELS["3230"] == "Nonin Connect 3230"


class TestNoninMatching:
    def test_match_proprietary_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[NONIN_SERVICE_UUID.upper()])
        assert len(registry.match(ad)) == 1

    def test_match_model_name(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(local_name="Nonin_3150"))) == 1

    def test_sig_plx_alone_does_not_match(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=["1822"])
        assert registry.match(ad) == []


class TestNoninParse:
    def test_proprietary_uuid_parses(self):
        result = NoninParser().parse(_make_ad(service_uuids=[NONIN_SERVICE_UUID]))
        assert result is not None
        assert result.parser_name == "nonin"
        assert result.device_class == "medical"
        assert result.metadata["vendor"] == "Nonin Medical"
        assert result.metadata["nonin_service"] is True

    def test_name_model_decode_underscore(self):
        result = NoninParser().parse(_make_ad(local_name="Nonin_3230"))
        assert result is not None
        assert result.metadata["model"] == "3230"
        assert result.metadata["model_name"] == "Nonin Connect 3230"
        assert result.metadata["device_name"] == "Nonin_3230"

    def test_name_model_decode_space(self):
        result = NoninParser().parse(_make_ad(local_name="Nonin 3150"))
        assert result.metadata["model"] == "3150"
        assert result.metadata["model_name"] == "WristOx2 3150"

    def test_unknown_model_number_still_parses(self):
        result = NoninParser().parse(_make_ad(local_name="Nonin_9999"))
        assert result is not None
        assert result.metadata["model"] == "9999"
        assert "model_name" not in result.metadata

    def test_plx_service_noted_when_paired_with_nonin_signal(self):
        result = NoninParser().parse(
            _make_ad(service_uuids=[NONIN_SERVICE_UUID, "1822"])
        )
        assert result.metadata["plx_service_advertised"] is True

    def test_plx_service_alone_returns_none(self):
        assert NoninParser().parse(_make_ad(service_uuids=["1822"])) is None

    def test_identity_hash_mac_based(self):
        result = NoninParser().parse(_make_ad(local_name="Nonin_3150"))
        expected = hashlib.sha256(b"nonin:00:1C:05:11:22:33").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_unrelated_device_returns_none(self):
        assert NoninParser().parse(_make_ad(local_name="Some Oximeter")) is None

    def test_name_prefix_without_model_returns_none(self):
        # "Nonintrusive Widget" must not be mistaken for a Nonin oximeter.
        assert NoninParser().parse(_make_ad(local_name="Nonintrusive Widget")) is None


class TestNoninDoesNotDoubleClaimWithOmron:
    """omron.py matches the SIG PLX UUID 0x1822, which Nonin oximeters also
    advertise. A SIG-UUID-only hit on a device Nonin owns by name or by its
    proprietary service UUID must not be claimed as an Omron device."""

    def test_omron_skips_nonin_name(self):
        from adwatch.plugins.omron import OmronParser
        ad = _make_ad(local_name="Nonin_3150", service_uuids=["1822"])
        assert OmronParser().parse(ad) is None

    def test_omron_skips_nonin_proprietary_uuid(self):
        from adwatch.plugins.omron import OmronParser
        ad = _make_ad(local_name=None,
                      service_uuids=["1822", NONIN_SERVICE_UUID])
        assert OmronParser().parse(ad) is None

    def test_omron_still_claims_its_own_plx_devices(self):
        from adwatch.plugins.omron import OmronParser
        ad = _make_ad(local_name="BLEsmart_00010112ABCDEF", service_uuids=["1822"])
        result = OmronParser().parse(ad)
        assert result is not None
        assert result.metadata["product_class"] == "pulse_oximeter"

    def test_omron_still_claims_anonymous_plx_devices(self):
        from adwatch.plugins.omron import OmronParser
        ad = _make_ad(local_name=None, service_uuids=["1822"])
        assert OmronParser().parse(ad) is not None
