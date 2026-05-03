"""Tests for Wyze plugin (Lock + EarBuds)."""

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.wyze import (
    WyzeParser,
    WYZE_EARBUDS_UUID,
    BATTERY_SERVICE_UUID,
)


def _make_ad(**kw):
    defaults = {"timestamp": "2025-01-01T00:00:00Z", "mac_address": "AA:BB:CC:DD:EE:FF",
                "address_type": "random", "manufacturer_data": None, "service_data": None}
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(name="wyze", service_uuid=WYZE_EARBUDS_UUID,
                     local_name_pattern=r"^(Wyze (Lock|Lock Bolt|Lock Keypad|Gunsafe)|DingDing)",
                     description="Wyze", version="1.0.0", core=False, registry=registry)
    class _P(WyzeParser):
        pass
    return _P


class TestWyzeMatching:
    def test_match_earbuds_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[WYZE_EARBUDS_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_wyze_lock_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="Wyze Lock 12AB34")
        assert len(registry.match(ad)) == 1

    def test_match_dingding_yunding_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="DingDing-XYZ")
        assert len(registry.match(ad)) == 1


class TestWyzeParsing:
    def test_earbuds_classified(self):
        ad = _make_ad(service_uuids=[WYZE_EARBUDS_UUID])
        result = WyzeParser().parse(ad)
        assert result is not None
        assert result.metadata["product_class"] == "earbuds"
        assert result.device_class == "audio"

    def test_lock_classified(self):
        ad = _make_ad(local_name="Wyze Lock 12AB34")
        result = WyzeParser().parse(ad)
        assert result.metadata["product_class"] == "lock"
        assert result.device_class == "lock"

    def test_lock_bolt(self):
        ad = _make_ad(local_name="Wyze Lock Bolt 88")
        result = WyzeParser().parse(ad)
        assert result.metadata["product_variant"] == "Lock Bolt"

    def test_gunsafe(self):
        ad = _make_ad(local_name="Wyze Gunsafe 001")
        result = WyzeParser().parse(ad)
        assert result.metadata["product_variant"] == "Gunsafe"
        assert result.metadata["sensitive"] is True

    def test_battery_uuid_alone_does_not_match(self):
        # 0x180F is SIG-generic; UUID alone would false-positive on
        # countless devices. Require name confirmation.
        ad = _make_ad(service_uuids=[BATTERY_SERVICE_UUID])
        result = WyzeParser().parse(ad)
        assert result is None

    def test_battery_uuid_plus_name_high_confidence(self):
        ad = _make_ad(service_uuids=[BATTERY_SERVICE_UUID],
                      local_name="Wyze Lock 12AB34")
        result = WyzeParser().parse(ad)
        assert result.metadata["confidence"] == "high"

    def test_basics(self):
        ad = _make_ad(service_uuids=[WYZE_EARBUDS_UUID])
        result = WyzeParser().parse(ad)
        assert result.parser_name == "wyze"
        assert result.beacon_type == "wyze"

    def test_returns_none_unrelated(self):
        ad = _make_ad(local_name="something")
        assert WyzeParser().parse(ad) is None
