"""Tests for KEF wireless speaker plugin."""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.kef import (
    KefParser,
    KEF_VENDOR_UUID,
    GAIA_SERVICE_UUID,
    FAST_PAIR_UUID,
)


def _make_ad(**kw):
    defaults = {"timestamp": "2025-01-01T00:00:00Z", "mac_address": "AA:BB:CC:DD:EE:FF",
                "address_type": "random", "manufacturer_data": None, "service_data": None}
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _kef_mfr(prefix=b"\x00\x00", project=0x10, status=0x80):
    """Build KEF 4-byte mfr-data: 2B vendor prefix + projectCode + statusBitmask."""
    return prefix + bytes([project, status])


def _register(registry):
    @register_parser(name="kef",
                     service_uuid=[KEF_VENDOR_UUID, GAIA_SERVICE_UUID],
                     local_name_pattern=r"^KEF ",
                     description="KEF", version="1.0.0", core=False,
                     registry=registry)
    class _P(KefParser):
        pass
    return _P


class TestKefMatching:
    def test_match_kef_vendor_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[KEF_VENDOR_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_gaia_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[GAIA_SERVICE_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_kef_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="KEF LS50 II Living Room")
        assert len(registry.match(ad)) == 1


class TestKefParsing:
    def test_decode_project_code(self):
        ad = _make_ad(local_name="KEF LS50 II",
                      manufacturer_data=_kef_mfr(project=0x42))
        result = KefParser().parse(ad)
        assert result is not None
        assert result.metadata["project_code"] == 0x42

    def test_status_power_on(self):
        ad = _make_ad(local_name="KEF LS50",
                      manufacturer_data=_kef_mfr(status=0x80))
        result = KefParser().parse(ad)
        assert result.metadata["is_power_on"] is True
        assert result.metadata["is_connected_with_bonded_device"] is False
        assert result.metadata["is_in_pairing_mode"] is False

    def test_status_bonded(self):
        ad = _make_ad(local_name="KEF LS50",
                      manufacturer_data=_kef_mfr(status=0x10))
        result = KefParser().parse(ad)
        assert result.metadata["is_connected_with_bonded_device"] is True

    def test_status_pairing(self):
        ad = _make_ad(local_name="KEF LS50",
                      manufacturer_data=_kef_mfr(status=0x01))
        result = KefParser().parse(ad)
        assert result.metadata["is_in_pairing_mode"] is True

    def test_status_all_set(self):
        ad = _make_ad(local_name="KEF LS50",
                      manufacturer_data=_kef_mfr(status=0x91))
        result = KefParser().parse(ad)
        assert result.metadata["is_power_on"] is True
        assert result.metadata["is_connected_with_bonded_device"] is True
        assert result.metadata["is_in_pairing_mode"] is True

    def test_short_mfr_data_uuid_match_only(self):
        # No 4-byte mfr-data but UUID present → still match, no status fields
        ad = _make_ad(service_uuids=[KEF_VENDOR_UUID])
        result = KefParser().parse(ad)
        assert result is not None
        assert "project_code" not in result.metadata

    def test_basics(self):
        ad = _make_ad(local_name="KEF Mu7", manufacturer_data=_kef_mfr())
        result = KefParser().parse(ad)
        assert result.parser_name == "kef"
        assert result.beacon_type == "kef"
        assert result.device_class == "audio"

    def test_identity_uses_project_and_mac(self):
        ad = _make_ad(local_name="KEF LS50",
                      manufacturer_data=_kef_mfr(project=0x10),
                      mac_address="11:22:33:44:55:66")
        result = KefParser().parse(ad)
        expected = hashlib.sha256(b"kef:10:11:22:33:44:55:66").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_returns_none_unrelated(self):
        assert KefParser().parse(_make_ad(local_name="Other")) is None
