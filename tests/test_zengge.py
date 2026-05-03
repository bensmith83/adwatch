"""Tests for Zengge / Magic Light bulb plugin."""

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.zengge import ZenggeParser, ZENGGE_HM10_UUID


def _make_ad(**kw):
    defaults = {"timestamp": "2025-01-01T00:00:00Z", "mac_address": "AA:BB:CC:DD:EE:FF",
                "address_type": "random", "manufacturer_data": None, "service_data": None}
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(name="zengge", service_uuid=ZENGGE_HM10_UUID,
                     local_name_pattern=r"^(LEDBlue|LEDBLE|LEDSpeaker|LEDShoe|LEDnet|FluxBlue|TIBURN)",
                     description="Zengge", version="1.0.0", core=False, registry=registry)
    class _P(ZenggeParser):
        pass
    return _P


class TestZenggeMatching:
    def test_match_ledble_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="LEDBLE-F40D2B")
        assert len(registry.match(ad)) == 1

    def test_match_fluxblue(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="FluxBlue-12345")
        assert len(registry.match(ad)) == 1

    def test_match_tiburn(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="TIBURN-XXXXX")
        assert len(registry.match(ad)) == 1

    def test_uuid_alone_does_not_match(self):
        # 0xFFE0 is the HM-10 commodity service — UUID alone would
        # false-positive on every HM-10-based product. Require a name hit.
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=["ffe0"])
        # Either zero or one match acceptable; but our parser should reject
        # UUID-only with no name signal.
        matches = registry.match(ad)
        if matches:
            # If the registry matched (because UUID alone is enough), the
            # parser itself should still return None.
            result = matches[0].parse(ad)
            assert result is None


class TestZenggeParsing:
    def test_ledble_brand(self):
        ad = _make_ad(local_name="LEDBLE-F40D2B")
        result = ZenggeParser().parse(ad)
        assert result is not None
        assert result.metadata["brand"] == "LEDBLE"

    def test_fluxblue_brand(self):
        ad = _make_ad(local_name="FluxBlue-AB1234")
        result = ZenggeParser().parse(ad)
        assert result.metadata["brand"] == "FluxBlue"

    def test_basics(self):
        ad = _make_ad(local_name="LEDBLE-F40D2B")
        result = ZenggeParser().parse(ad)
        assert result.parser_name == "zengge"
        assert result.beacon_type == "zengge"
        assert result.device_class == "smart_light"

    def test_returns_none_unrelated(self):
        ad = _make_ad(local_name="something")
        assert ZenggeParser().parse(ad) is None
