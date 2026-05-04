"""Tests for LG ThinQ appliance plugin."""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.lg_thinq import (
    LgThinqParser,
    LG_CID,
)


def _make_ad(**kw):
    defaults = {"timestamp": "2025-01-01T00:00:00Z", "mac_address": "AA:BB:CC:DD:EE:FF",
                "address_type": "random", "manufacturer_data": None, "service_data": None}
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _lg_mfr(prefix=b"\x00\x00\x00\x00",
            mac=b"\xAA\xBB\xCC\xDD\xEE\xFF",
            model_name=b"WashTower2",
            registered=True):
    """Build LG ThinQ mfr-data: CID 196 + 4B prefix + 6B MAC + UTF-8 model + flag byte."""
    cid = (LG_CID).to_bytes(2, "little")
    flag = b"\x01" if registered else b"\x00"
    return cid + prefix + mac + model_name + flag


def _register(registry):
    @register_parser(name="lg_thinq", company_id=LG_CID,
                     local_name_pattern=r"^(AD_|ad_|LG_Smart|LGE|LG_WashTower2|Signature)",
                     description="LG", version="1.0.0", core=False,
                     registry=registry)
    class _P(LgThinqParser):
        pass
    return _P


class TestLgThinqMatching:
    def test_match_cid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=_lg_mfr())
        assert len(registry.match(ad)) == 1

    def test_match_ad_prefix(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="AD_LGE_Refrigerator_001")
        assert len(registry.match(ad)) == 1

    def test_match_lg_smart_prefix(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="LG_Smart_AC_42")
        assert len(registry.match(ad)) == 1

    def test_match_lge_prefix(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="LGE-Oven-001")
        assert len(registry.match(ad)) == 1


class TestLgThinqParsing:
    def test_decode_mac_in_payload(self):
        ad = _make_ad(manufacturer_data=_lg_mfr(mac=b"\x11\x22\x33\x44\x55\x66"))
        result = LgThinqParser().parse(ad)
        assert result is not None
        assert result.metadata["embedded_mac"] == "11:22:33:44:55:66"

    def test_decode_model_name(self):
        ad = _make_ad(manufacturer_data=_lg_mfr(model_name=b"WashTower2 W9000"))
        result = LgThinqParser().parse(ad)
        assert result.metadata["model_name"] == "WashTower2 W9000"

    def test_registered_flag_true(self):
        ad = _make_ad(manufacturer_data=_lg_mfr(registered=True))
        result = LgThinqParser().parse(ad)
        assert result.metadata["registered"] is True

    def test_registered_flag_false(self):
        ad = _make_ad(manufacturer_data=_lg_mfr(registered=False))
        result = LgThinqParser().parse(ad)
        assert result.metadata["registered"] is False

    def test_unprovisioned_from_ad_prefix(self):
        ad = _make_ad(local_name="AD_LGE_Oven_42")
        result = LgThinqParser().parse(ad)
        assert result.metadata["provisioning_mode"] is True

    def test_provisioning_false_for_registered(self):
        ad = _make_ad(local_name="LG_Smart_AC", manufacturer_data=_lg_mfr(registered=True))
        result = LgThinqParser().parse(ad)
        assert result.metadata.get("provisioning_mode", False) is False

    def test_identity_uses_embedded_mac(self):
        ad = _make_ad(manufacturer_data=_lg_mfr(mac=b"\x11\x22\x33\x44\x55\x66"),
                      mac_address="00:00:00:00:00:00")
        result = LgThinqParser().parse(ad)
        expected = hashlib.sha256(b"lg_thinq:11:22:33:44:55:66").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_basics(self):
        ad = _make_ad(manufacturer_data=_lg_mfr())
        result = LgThinqParser().parse(ad)
        assert result.parser_name == "lg_thinq"
        assert result.beacon_type == "lg_thinq"
        assert result.device_class == "appliance"

    def test_returns_none_unrelated(self):
        assert LgThinqParser().parse(_make_ad(local_name="Other")) is None
