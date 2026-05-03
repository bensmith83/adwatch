"""Tests for Alibaba AIS plugin (ECOVACS / AliGenie OEMs)."""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.alibaba_ais import AlibabaAisParser, ALIBABA_CID


def _make_ad(**kw):
    defaults = {"timestamp": "2025-01-01T00:00:00Z", "mac_address": "AA:BB:CC:DD:EE:FF",
                "address_type": "random", "manufacturer_data": None, "service_data": None}
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _ais_basic_mfr(version=0, fmask=0x00, pid_be=b"\x00\x00\x00\x42",
                   bd_addr_be=b"\xAA\xBB\xCC\xDD\xEE\xFF"):
    """Build AIS basic-subtype mfr-data: CID + (subtype<<4 | version) + fmask + PID(BE) + MAC(reversed)."""
    cid = (ALIBABA_CID).to_bytes(2, "little")
    subtype_byte = (0x08 << 4) | (version & 0x0F)
    return cid + bytes([subtype_byte, fmask]) + pid_be + bytes(reversed(bd_addr_be))


def _ais_beacon_mfr(version=0, fmask=0x00, pid_lo=0x1234,
                    bd_addr_be=b"\x11\x22\x33\x44\x55\x66"):
    cid = (ALIBABA_CID).to_bytes(2, "little")
    subtype_byte = (0x09 << 4) | (version & 0x0F)
    return (cid + bytes([subtype_byte, fmask])
            + pid_lo.to_bytes(2, "little")
            + bytes(reversed(bd_addr_be)))


def _register(registry):
    @register_parser(name="alibaba_ais", company_id=ALIBABA_CID,
                     local_name_pattern=r"^(DEEBOT|WINBOT|ECOVACS|ALI-)",
                     description="Alibaba AIS", version="1.0.0", core=False, registry=registry)
    class _P(AlibabaAisParser):
        pass
    return _P


class TestAlibabaAisMatching:
    def test_match_cid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=_ais_basic_mfr())
        assert len(registry.match(ad)) == 1

    def test_match_deebot_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="DEEBOT-1234AB")
        assert len(registry.match(ad)) == 1

    def test_match_winbot_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="WINBOT-88C2F3")
        assert len(registry.match(ad)) == 1


class TestAlibabaAisBasicSubtype:
    def test_subtype_basic(self):
        ad = _make_ad(manufacturer_data=_ais_basic_mfr())
        result = AlibabaAisParser().parse(ad)
        assert result is not None
        assert result.metadata["ais_subtype"] == "basic"

    def test_pid_decoded_be(self):
        ad = _make_ad(manufacturer_data=_ais_basic_mfr(pid_be=b"\x00\x00\xAB\xCD"))
        result = AlibabaAisParser().parse(ad)
        assert result.metadata["product_id"] == 0xABCD

    def test_bd_addr_decoded(self):
        ad = _make_ad(manufacturer_data=_ais_basic_mfr(bd_addr_be=b"\x11\x22\x33\x44\x55\x66"))
        result = AlibabaAisParser().parse(ad)
        assert result.metadata["embedded_mac"] == "11:22:33:44:55:66"

    def test_version_extracted(self):
        ad = _make_ad(manufacturer_data=_ais_basic_mfr(version=2))
        result = AlibabaAisParser().parse(ad)
        assert result.metadata["ais_version"] == 2

    def test_fmask_surfaced(self):
        ad = _make_ad(manufacturer_data=_ais_basic_mfr(fmask=0x42))
        result = AlibabaAisParser().parse(ad)
        assert result.metadata["fmask"] == 0x42


class TestAlibabaAisBeaconSubtype:
    def test_subtype_beacon(self):
        ad = _make_ad(manufacturer_data=_ais_beacon_mfr())
        result = AlibabaAisParser().parse(ad)
        assert result.metadata["ais_subtype"] == "beacon"

    def test_beacon_pid_low_2_bytes(self):
        ad = _make_ad(manufacturer_data=_ais_beacon_mfr(pid_lo=0xCAFE))
        result = AlibabaAisParser().parse(ad)
        assert result.metadata["product_id"] == 0xCAFE


class TestAlibabaAisIdentity:
    def test_identity_uses_bd_addr(self):
        ad = _make_ad(manufacturer_data=_ais_basic_mfr(bd_addr_be=b"\xCA\xFE\xBA\xBE\x01\x02"),
                      mac_address="00:00:00:00:00:00")
        result = AlibabaAisParser().parse(ad)
        expected = hashlib.sha256(b"alibaba_ais:CA:FE:BA:BE:01:02").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_basics(self):
        ad = _make_ad(manufacturer_data=_ais_basic_mfr())
        result = AlibabaAisParser().parse(ad)
        assert result.parser_name == "alibaba_ais"
        assert result.beacon_type == "alibaba_ais"

    def test_returns_none_unrelated(self):
        ad = _make_ad(local_name="something")
        assert AlibabaAisParser().parse(ad) is None
