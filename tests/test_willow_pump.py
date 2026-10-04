"""Tests for Willow breast pump presence plugin.

Per apk-ble-hunting/reports/willow-go_passive.md: name prefixes ^WillowGo-
(Go) and ^Willow- (3.0/360). Mfr-data layout/CID unknown -> recorded raw only.
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser
from adwatch.plugins.willow_pump import WillowPumpParser, WILLOW_NAME_PATTERN


def _make_ad(**kw):
    d = dict(timestamp="2026-10-01T00:00:00Z", mac_address="D0:11:22:33:44:55",
             address_type="random", manufacturer_data=None, service_data=None)
    d.update(kw)
    return RawAdvertisement(**d)


def _register(registry):
    @register_parser(name="willow_pump", local_name_pattern=WILLOW_NAME_PATTERN,
                     description="Willow", version="1.0.0", core=False,
                     registry=registry)
    class _P(WillowPumpParser):
        pass
    return _P


def test_matches_go_and_legacy():
    reg = ParserRegistry()
    _register(reg)
    assert len(reg.match(_make_ad(local_name="WillowGo-AB12"))) == 1
    assert len(reg.match(_make_ad(local_name="Willow-XY99"))) == 1


def test_no_match_unanchored_or_other():
    reg = ParserRegistry()
    _register(reg)
    assert reg.match(_make_ad(local_name="MyWillow-1")) == []
    assert reg.match(_make_ad(local_name="Willow 360")) == []
    assert reg.match(_make_ad(local_name="WillowTree")) == []


def test_parse_go():
    r = WillowPumpParser().parse(_make_ad(local_name="WillowGo-AB12"))
    m = r.metadata
    assert m["generation"] == "Go"
    assert m["name_suffix"] == "AB12"
    assert m["sensitive"] is True
    assert r.device_class == "medical"
    assert r.parser_name == "willow_pump"
    assert r.identifier_hash == hashlib.sha256(
        b"willow_pump:D0:11:22:33:44:55:AB12").hexdigest()[:16]


def test_parse_legacy_with_mfr_data():
    ad = _make_ad(local_name="Willow-XY99",
                  manufacturer_data=bytes([0x34, 0x12, 0xAA, 0xBB]))
    r = WillowPumpParser().parse(ad)
    m = r.metadata
    assert m["generation"] == "3.0/360"
    assert m["name_suffix"] == "XY99"
    assert m["mfr_company_id"] == 0x1234
    assert m["mfr_data_hex"] == "3412aabb"
    assert r.raw_payload_hex == "3412aabb"


def test_parse_rejects_non_willow():
    assert WillowPumpParser().parse(_make_ad(local_name="Pump-1")) is None
    assert WillowPumpParser().parse(_make_ad()) is None


def test_default_registry_has_willow():
    from adwatch.registry import _default_registry
    import adwatch.plugins.willow_pump  # noqa: F401
    assert "willow_pump" in [p.name for p in _default_registry.get_all()]
