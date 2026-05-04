"""Tests for Meross plugin (v1 RFBL/MRBL + v2 MS605)."""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.meross import (
    MerossParser,
    MEROSS_V1_UUID,
    MEROSS_V2_CID,
)


def _make_ad(**kw):
    defaults = {"timestamp": "2025-01-01T00:00:00Z", "mac_address": "AA:BB:CC:DD:EE:FF",
                "address_type": "random", "manufacturer_data": None, "service_data": None}
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _ms605_mfr(subdev=0xC0, body=b"\x00\x00\x00"):
    """v2 mfr-data: CID 0xFFFF + TLV (type, length, subdev, body)."""
    cid = (MEROSS_V2_CID).to_bytes(2, "little")
    tlv = bytes([0x01, len(body) + 1, subdev]) + body
    return cid + tlv


def _register(registry):
    @register_parser(name="meross",
                     company_id=MEROSS_V2_CID,
                     service_uuid=MEROSS_V1_UUID,
                     local_name_pattern=r"^(RFBL_|MRBL_)",
                     description="Meross", version="1.0.0", core=False,
                     registry=registry)
    class _P(MerossParser):
        pass
    return _P


class TestMerossMatching:
    def test_match_v1_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[MEROSS_V1_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_v1_name_rfbl(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="RFBL_A1B2C3D4E5F6")
        assert len(registry.match(ad)) == 1

    def test_match_v1_name_mrbl(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="MRBL_AABBCCDDEEFF")
        assert len(registry.match(ad)) == 1

    def test_match_v2_cid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=_ms605_mfr())
        assert len(registry.match(ad)) == 1


class TestMerossV1Parsing:
    def test_v1_uuid_classified(self):
        ad = _make_ad(service_uuids=[MEROSS_V1_UUID])
        result = MerossParser().parse(ad)
        assert result is not None
        assert result.metadata["product_family"] == "meross_v1"

    def test_rfbl_name_extracts_mac(self):
        ad = _make_ad(local_name="RFBL_A1B2C3D4E5F6")
        result = MerossParser().parse(ad)
        assert result.metadata["mac_in_name"] == "A1:B2:C3:D4:E5:F6"
        assert result.metadata["product_family"] == "meross_v1"

    def test_mrbl_name_extracts_mac(self):
        ad = _make_ad(local_name="MRBL_AABBCCDDEEFF")
        result = MerossParser().parse(ad)
        assert result.metadata["mac_in_name"] == "AA:BB:CC:DD:EE:FF"

    def test_v1_identity_uses_mac_in_name(self):
        ad = _make_ad(local_name="RFBL_A1B2C3D4E5F6", mac_address="00:00:00:00:00:00")
        result = MerossParser().parse(ad)
        expected = hashlib.sha256(b"meross:A1:B2:C3:D4:E5:F6").hexdigest()[:16]
        assert result.identifier_hash == expected


class TestMerossV2Parsing:
    def test_ms605_subdev_byte_recognized(self):
        ad = _make_ad(manufacturer_data=_ms605_mfr(subdev=0xC0))
        result = MerossParser().parse(ad)
        assert result is not None
        assert result.metadata["subdev_type"] == "ms605"
        assert result.metadata["product_family"] == "meross_v2"

    def test_unknown_subdev_byte(self):
        ad = _make_ad(manufacturer_data=_ms605_mfr(subdev=0x42))
        result = MerossParser().parse(ad)
        assert result.metadata["subdev_type"] == "unknown_0x42"


class TestMerossBasics:
    def test_basics_v1(self):
        ad = _make_ad(service_uuids=[MEROSS_V1_UUID])
        result = MerossParser().parse(ad)
        assert result.parser_name == "meross"
        assert result.beacon_type == "meross"
        assert result.device_class == "smart_home"

    def test_returns_none_unrelated(self):
        assert MerossParser().parse(_make_ad(local_name="Other")) is None
