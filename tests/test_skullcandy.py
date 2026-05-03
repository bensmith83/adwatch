"""Tests for Skullcandy Skull-iQ plugin."""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.skullcandy import (
    SkullcandyParser,
    SKULLCANDY_CID,
    MODEL_ID_TABLE,
)


def _make_ad(**kw):
    defaults = {"timestamp": "2025-01-01T00:00:00Z", "mac_address": "AA:BB:CC:DD:EE:FF",
                "address_type": "random", "manufacturer_data": None, "service_data": None}
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _skull_mfr(skip=0x00, model_id=9, mac=b"\xAA\xBB\xCC\xDD\xEE\xFF"):
    """Build Skullcandy mfr-data: CID 0x07C9 + skip byte + model id + 6B MAC."""
    cid = (SKULLCANDY_CID).to_bytes(2, "little")
    return cid + bytes([skip, model_id]) + mac


def _register(registry):
    @register_parser(name="skullcandy", company_id=SKULLCANDY_CID,
                     local_name_pattern=r"^(Grind|Sesh Boost|Push Active|CHP\d{3}|T\d{2,3}|Method|Skullcandy)",
                     description="Skullcandy", version="1.0.0", core=False, registry=registry)
    class _P(SkullcandyParser):
        pass
    return _P


class TestSkullcandyMatching:
    def test_match_cid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=_skull_mfr())
        assert len(registry.match(ad)) == 1

    def test_match_grind_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="Grind")
        assert len(registry.match(ad)) == 1

    def test_match_method_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="Method 540 ANC")
        assert len(registry.match(ad)) == 1


class TestSkullcandyParsing:
    def test_grind_model(self):
        ad = _make_ad(manufacturer_data=_skull_mfr(model_id=9))
        result = SkullcandyParser().parse(ad)
        assert result is not None
        assert result.metadata["model"] == "GRIND"

    def test_chp200_model(self):
        ad = _make_ad(manufacturer_data=_skull_mfr(model_id=22))
        result = SkullcandyParser().parse(ad)
        assert result.metadata["model"] == "CHP200"

    def test_t99_plus(self):
        ad = _make_ad(manufacturer_data=_skull_mfr(model_id=29))
        result = SkullcandyParser().parse(ad)
        assert result.metadata["model"] == "T99_PLUS"

    def test_t120_method540(self):
        ad = _make_ad(manufacturer_data=_skull_mfr(model_id=45))
        result = SkullcandyParser().parse(ad)
        assert result.metadata["model"] == "T120"

    def test_unknown_model_id(self):
        ad = _make_ad(manufacturer_data=_skull_mfr(model_id=0xEE))
        result = SkullcandyParser().parse(ad)
        assert result.metadata["model"].startswith("unknown_")

    def test_embedded_mac(self):
        ad = _make_ad(manufacturer_data=_skull_mfr(mac=b"\x11\x22\x33\x44\x55\x66"))
        result = SkullcandyParser().parse(ad)
        assert result.metadata["embedded_mac"] == "11:22:33:44:55:66"

    def test_identity_uses_embedded_mac(self):
        ad = _make_ad(manufacturer_data=_skull_mfr(mac=b"\xCA\xFE\xBA\xBE\x01\x02"),
                      mac_address="00:00:00:00:00:00")
        result = SkullcandyParser().parse(ad)
        expected = hashlib.sha256(b"skullcandy:CA:FE:BA:BE:01:02").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_basics(self):
        ad = _make_ad(manufacturer_data=_skull_mfr())
        result = SkullcandyParser().parse(ad)
        assert result.parser_name == "skullcandy"
        assert result.beacon_type == "skullcandy"
        assert result.device_class == "audio"

    def test_returns_none_unrelated(self):
        ad = _make_ad(local_name="something")
        assert SkullcandyParser().parse(ad) is None
