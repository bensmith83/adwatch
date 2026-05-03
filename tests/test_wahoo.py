"""Tests for Wahoo Fitness plugin."""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.wahoo import (
    WahooParser,
    WAHOO_CID,
    WAHOO_SERVICE_UUIDS,
)


def _make_ad(**kw):
    defaults = {"timestamp": "2025-01-01T00:00:00Z", "mac_address": "AA:BB:CC:DD:EE:FF",
                "address_type": "random", "manufacturer_data": None, "service_data": None}
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _wahoo_mfr(product_id=27, hw_version=1, extra=b""):
    """Build Wahoo ELEMNT mfr-data: CID 508 + productId LE16 + hwVersion LE16 + extra."""
    return ((WAHOO_CID).to_bytes(2, "little")
            + product_id.to_bytes(2, "little")
            + hw_version.to_bytes(2, "little")
            + extra)


def _ftms_mfr(fe_type=1, cap_flags=0x02):
    """Build Wahoo FTMS mfr-data: CID 508 + FETypeCode + capability flags."""
    return ((WAHOO_CID).to_bytes(2, "little")
            + bytes([fe_type, cap_flags]))


def _register(registry):
    @register_parser(name="wahoo", company_id=WAHOO_CID,
                     service_uuid=WAHOO_SERVICE_UUIDS,
                     local_name_pattern=r"^(TICKR|KICKR|ELEMNT|HEADWIND|POWRLINK|TRACKR|RFLKT|RUNNR|MIRROR|Dreadmill)",
                     description="Wahoo", version="1.0.0", core=False,
                     registry=registry)
    class _P(WahooParser):
        pass
    return _P


class TestWahooMatching:
    def test_match_cid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=_wahoo_mfr())
        assert len(registry.match(ad)) == 1

    def test_match_elemnt_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=["ee06"])
        assert len(registry.match(ad)) == 1

    def test_match_dfu_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=["ee0a"])
        assert len(registry.match(ad)) == 1

    def test_match_tickr_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="TICKR 3A6B")
        assert len(registry.match(ad)) == 1

    def test_match_elemnt_bolt_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="ELEMNT BOLT 12ABCD")
        assert len(registry.match(ad)) == 1

    def test_match_kickr_bike_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="KICKR BIKE ABCDE")
        assert len(registry.match(ad)) == 1


class TestWahooParsing:
    def test_elemnt_product_id(self):
        ad = _make_ad(local_name="ELEMNT BOLT 12ABCD",
                      manufacturer_data=_wahoo_mfr(product_id=56, hw_version=2))
        result = WahooParser().parse(ad)
        assert result is not None
        assert result.metadata["product_id"] == 56
        assert result.metadata["hw_version"] == 2

    def test_elemnt_family_from_name(self):
        ad = _make_ad(local_name="ELEMNT BOLT 12ABCD")
        result = WahooParser().parse(ad)
        assert result.metadata["product_family"] == "ELEMNT"

    def test_tickr_family(self):
        ad = _make_ad(local_name="TICKR 3A6B")
        result = WahooParser().parse(ad)
        assert result.metadata["product_family"] == "TICKR"

    def test_kickr_family(self):
        ad = _make_ad(local_name="KICKR BIKE ABCDE")
        result = WahooParser().parse(ad)
        assert result.metadata["product_family"] == "KICKR"

    def test_serial_suffix_extracted(self):
        ad = _make_ad(local_name="TICKR 3A6B")
        result = WahooParser().parse(ad)
        assert result.metadata["serial_suffix"] == "3A6B"

    def test_dfu_uuid_flag(self):
        ad = _make_ad(service_uuids=["ee0a"])
        result = WahooParser().parse(ad)
        assert result.metadata["dfu_mode"] is True

    def test_ftms_with_wahoo_cid_matches(self):
        # Wahoo CID present even on FTMS payload — match should fire.
        # We don't try to disambiguate ELEMNT vs FTMS payload semantics
        # here; that's a follow-up.
        ad = _make_ad(service_uuids=["1826"],
                      manufacturer_data=_ftms_mfr(fe_type=2, cap_flags=0x07))
        result = WahooParser().parse(ad)
        assert result is not None
        assert result.metadata["vendor"] == "Wahoo"

    def test_identity_uses_serial_suffix(self):
        ad = _make_ad(local_name="TICKR 3A6B",
                      mac_address="11:22:33:44:55:66")
        result = WahooParser().parse(ad)
        expected = hashlib.sha256(b"wahoo:TICKR:3A6B").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_basics(self):
        ad = _make_ad(local_name="TICKR 3A6B")
        result = WahooParser().parse(ad)
        assert result.parser_name == "wahoo"
        assert result.beacon_type == "wahoo"
        assert result.device_class == "fitness_sensor"

    def test_returns_none_unrelated(self):
        assert WahooParser().parse(_make_ad(local_name="Other")) is None
