"""Tests for SimpliSafe Home Security plugin."""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.simplisafe import (
    SimpliSafeParser,
    SIMPLISAFE_CID,
    BASESTATION_UUIDS,
    LOCK_APP_UUID,
    NORDIC_DFU_UUID,
)


def _make_ad(**kw):
    defaults = {"timestamp": "2025-01-01T00:00:00Z", "mac_address": "AA:BB:CC:DD:EE:FF",
                "address_type": "random", "manufacturer_data": None, "service_data": None}
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _ss_mfr(serial_tag=b"\xDE\xAD\xBE\xEF", ext_tag=b"\xCA\xFE\xBA\xBE"):
    return (SIMPLISAFE_CID).to_bytes(2, "little") + serial_tag + ext_tag


def _register(registry):
    @register_parser(name="simplisafe", company_id=SIMPLISAFE_CID,
                     service_uuid=BASESTATION_UUIDS + [LOCK_APP_UUID],
                     description="SimpliSafe", version="1.0.0", core=False,
                     registry=registry)
    class _P(SimpliSafeParser):
        pass
    return _P


class TestSimpliSafeMatching:
    def test_match_by_cid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=_ss_mfr())
        assert len(registry.match(ad)) == 1

    def test_match_basestation_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=["00000d18-0000-1000-8000-00805f9b34fb"])
        assert len(registry.match(ad)) == 1

    def test_match_basestation_short_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=["0d18"])
        assert len(registry.match(ad)) == 1

    def test_match_lock_app_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[LOCK_APP_UUID])
        assert len(registry.match(ad)) == 1


class TestSimpliSafeParsing:
    def test_basestation_classification(self):
        ad = _make_ad(manufacturer_data=_ss_mfr(),
                      service_uuids=["00000d18-0000-1000-8000-00805f9b34fb"])
        result = SimpliSafeParser().parse(ad)
        assert result is not None
        assert result.metadata["product_class"] == "base_station"

    def test_lock_app_classification(self):
        ad = _make_ad(manufacturer_data=_ss_mfr(), service_uuids=[LOCK_APP_UUID])
        result = SimpliSafeParser().parse(ad)
        assert result.metadata["product_class"] == "smart_lock"
        assert result.metadata["mode"] == "application"

    def test_lock_dfu_classification(self):
        ad = _make_ad(manufacturer_data=_ss_mfr(),
                      service_uuids=[NORDIC_DFU_UUID])
        result = SimpliSafeParser().parse(ad)
        assert result.metadata["product_class"] == "smart_lock"
        assert result.metadata["mode"] == "dfu"

    def test_dfu_alone_does_not_match(self):
        # Nordic DFU UUID alone (without SimpliSafe CID) should NOT match —
        # otherwise we steal sightings from every Nordic-DFU bootloader.
        ad = _make_ad(service_uuids=[NORDIC_DFU_UUID])
        result = SimpliSafeParser().parse(ad)
        assert result is None

    def test_serial_tag_extracted(self):
        ad = _make_ad(manufacturer_data=_ss_mfr(serial_tag=b"\x11\x22\x33\x44"))
        result = SimpliSafeParser().parse(ad)
        assert result.metadata["serial_tag_hex"] == "11223344"

    def test_extended_serial_tag(self):
        ad = _make_ad(manufacturer_data=_ss_mfr(ext_tag=b"\x55\x66\x77\x88"))
        result = SimpliSafeParser().parse(ad)
        assert result.metadata["extended_serial_tag_hex"] == "55667788"

    def test_identity_uses_serial_tag(self):
        ad = _make_ad(manufacturer_data=_ss_mfr(serial_tag=b"\xDE\xAD\xBE\xEF"),
                      mac_address="11:22:33:44:55:66")
        result = SimpliSafeParser().parse(ad)
        expected = hashlib.sha256(b"simplisafe:deadbeef").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_basics(self):
        result = SimpliSafeParser().parse(_make_ad(manufacturer_data=_ss_mfr()))
        assert result.parser_name == "simplisafe"
        assert result.beacon_type == "simplisafe"
        assert result.device_class == "security"

    def test_returns_none_unrelated(self):
        assert SimpliSafeParser().parse(_make_ad(local_name="Other")) is None
