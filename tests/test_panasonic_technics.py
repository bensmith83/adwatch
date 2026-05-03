"""Tests for Panasonic Technics audio plugin."""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.panasonic_technics import (
    PanasonicTechnicsParser,
    PANASONIC_CID,
    AIROHA_PRIMARY_UUID,
    AIROHA_TRSPX_UUID,
)


def _make_ad(**kw):
    defaults = {"timestamp": "2025-01-01T00:00:00Z", "mac_address": "AA:BB:CC:DD:EE:FF",
                "address_type": "random", "manufacturer_data": None, "service_data": None}
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _technics_mfr(header=b"\x00\x01\x02\x03", model=0x10,
                   bd_addr=b"\xAA\xBB\xCC\xDD\xEE\xFF"):
    """Build Panasonic Technics mfr-data: CID + 4B header + model + 6B BR/EDR MAC."""
    cid = (PANASONIC_CID).to_bytes(2, "little")
    return cid + header + bytes([model]) + bd_addr


def _register(registry):
    @register_parser(name="panasonic_technics",
                     company_id=PANASONIC_CID,
                     service_uuid=[AIROHA_PRIMARY_UUID, AIROHA_TRSPX_UUID],
                     local_name_pattern=r"^(EAH-|Technics EAH-|LE-EAH-)",
                     description="Technics", version="1.0.0", core=False,
                     registry=registry)
    class _P(PanasonicTechnicsParser):
        pass
    return _P


class TestTechnicsMatching:
    def test_match_cid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=_technics_mfr())
        assert len(registry.match(ad)) == 1

    def test_match_name_eah(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="EAH-AZ70W")
        assert len(registry.match(ad)) == 1

    def test_match_name_technics(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="Technics EAH-AZ80")
        assert len(registry.match(ad)) == 1

    def test_match_name_le_legacy(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="LE-EAH-AZ70W")
        assert len(registry.match(ad)) == 1


class TestTechnicsParsing:
    def test_decodes_model_byte(self):
        ad = _make_ad(manufacturer_data=_technics_mfr(model=0x42))
        result = PanasonicTechnicsParser().parse(ad)
        assert result is not None
        assert result.metadata["model_byte"] == 0x42

    def test_decodes_bd_addr(self):
        ad = _make_ad(manufacturer_data=_technics_mfr(bd_addr=b"\x11\x22\x33\x44\x55\x66"))
        result = PanasonicTechnicsParser().parse(ad)
        assert result.metadata["bd_addr"] == "11:22:33:44:55:66"

    def test_identity_uses_bd_addr(self):
        ad = _make_ad(manufacturer_data=_technics_mfr(bd_addr=b"\xCA\xFE\xBA\xBE\x01\x02"),
                      mac_address="00:00:00:00:00:00")
        result = PanasonicTechnicsParser().parse(ad)
        expected = hashlib.sha256(b"panasonic_technics:CA:FE:BA:BE:01:02").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_falls_back_to_mac(self):
        ad = _make_ad(local_name="EAH-AZ70W", mac_address="11:22:33:44:55:66")
        result = PanasonicTechnicsParser().parse(ad)
        expected = hashlib.sha256(b"panasonic_technics:11:22:33:44:55:66").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_extract_model_from_name(self):
        ad = _make_ad(local_name="EAH-AZ100")
        result = PanasonicTechnicsParser().parse(ad)
        assert result.metadata["model"] == "EAH-AZ100"

    def test_strip_technics_prefix_from_model(self):
        ad = _make_ad(local_name="Technics EAH-AZ80")
        result = PanasonicTechnicsParser().parse(ad)
        assert result.metadata["model"] == "EAH-AZ80"
        assert result.metadata["technics_branded"] is True

    def test_le_prefix_flag(self):
        ad = _make_ad(local_name="LE-EAH-AZ70W")
        result = PanasonicTechnicsParser().parse(ad)
        assert result.metadata["model"] == "EAH-AZ70W"
        assert result.metadata["le_only_variant"] is True

    def test_short_payload_no_decode(self):
        cid = (PANASONIC_CID).to_bytes(2, "little")
        ad = _make_ad(manufacturer_data=cid + b"\x00\x01")
        result = PanasonicTechnicsParser().parse(ad)
        assert result is not None
        assert "bd_addr" not in result.metadata

    def test_basics(self):
        result = PanasonicTechnicsParser().parse(_make_ad(local_name="EAH-AZ70W"))
        assert result.parser_name == "panasonic_technics"
        assert result.beacon_type == "panasonic_technics"
        assert result.device_class == "audio"

    def test_returns_none_unrelated(self):
        assert PanasonicTechnicsParser().parse(_make_ad(local_name="Other")) is None
