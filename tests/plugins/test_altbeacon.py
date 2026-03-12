"""Tests for AltBeacon parser plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.altbeacon import AltBeaconParser


@pytest.fixture
def parser():
    return AltBeaconParser()


def make_raw(manufacturer_data=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-06T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        service_data=None,
        service_uuids=[],
    )
    defaults.update(kwargs)
    return RawAdvertisement(manufacturer_data=manufacturer_data, **defaults)


# AltBeacon layout (26 bytes total):
#   [0:2]   company ID (little-endian, any)
#   [2:4]   beacon code 0xBEAC (big-endian)
#   [4:20]  UUID (16 bytes)
#   [20:22] major (uint16 BE)
#   [22:24] minor (uint16 BE)
#   [24]    reference RSSI (signed int8)
#   [25]    MFG reserved (1 byte)

TEST_UUID_BYTES = bytes.fromhex("e2c56db5dffb48d2b060d0f5a71096e0")
TEST_UUID = "e2c56db5-dffb-48d2-b060-d0f5a71096e0"
TEST_MAJOR = 1
TEST_MINOR = 2
TEST_REF_RSSI = -65  # 0xBF as signed int8
TEST_MFG_RESERVED = 0x42
TEST_COMPANY_ID = 0x0118  # Radius Networks


def build_altbeacon_data(
    company_id=TEST_COMPANY_ID,
    beacon_code=b"\xBE\xAC",
    uuid_bytes=TEST_UUID_BYTES,
    major=TEST_MAJOR,
    minor=TEST_MINOR,
    ref_rssi=TEST_REF_RSSI,
    mfg_reserved=TEST_MFG_RESERVED,
):
    return (
        struct.pack("<H", company_id)
        + beacon_code
        + uuid_bytes
        + struct.pack(">H", major)
        + struct.pack(">H", minor)
        + struct.pack("b", ref_rssi)
        + bytes([mfg_reserved])
    )


ALTBEACON_DATA = build_altbeacon_data()


class TestAltBeaconParsing:
    def test_parse_valid_altbeacon(self, parser):
        raw = make_raw(manufacturer_data=ALTBEACON_DATA)
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(manufacturer_data=ALTBEACON_DATA)
        result = parser.parse(raw)
        assert result.parser_name == "altbeacon"

    def test_device_class(self, parser):
        raw = make_raw(manufacturer_data=ALTBEACON_DATA)
        result = parser.parse(raw)
        assert result.device_class == "beacon"

    def test_beacon_type(self, parser):
        raw = make_raw(manufacturer_data=ALTBEACON_DATA)
        result = parser.parse(raw)
        assert result.beacon_type == "altbeacon"

    def test_uuid_parsed(self, parser):
        raw = make_raw(manufacturer_data=ALTBEACON_DATA)
        result = parser.parse(raw)
        assert result.metadata["uuid"] == TEST_UUID

    def test_major_parsed(self, parser):
        raw = make_raw(manufacturer_data=ALTBEACON_DATA)
        result = parser.parse(raw)
        assert result.metadata["major"] == TEST_MAJOR

    def test_minor_parsed(self, parser):
        raw = make_raw(manufacturer_data=ALTBEACON_DATA)
        result = parser.parse(raw)
        assert result.metadata["minor"] == TEST_MINOR

    def test_reference_rssi(self, parser):
        raw = make_raw(manufacturer_data=ALTBEACON_DATA)
        result = parser.parse(raw)
        assert result.metadata["reference_rssi"] == TEST_REF_RSSI

    def test_mfg_reserved(self, parser):
        raw = make_raw(manufacturer_data=ALTBEACON_DATA)
        result = parser.parse(raw)
        assert result.metadata["mfg_reserved"] == TEST_MFG_RESERVED

    def test_raw_payload_hex(self, parser):
        """raw_payload_hex should be the payload after company ID."""
        raw = make_raw(manufacturer_data=ALTBEACON_DATA)
        result = parser.parse(raw)
        assert result.raw_payload_hex == ALTBEACON_DATA[2:].hex()


class TestAltBeaconIdentity:
    def test_identity_hash_value(self, parser):
        """Identity = SHA256(uuid:major:minor)[:16]."""
        raw = make_raw(manufacturer_data=ALTBEACON_DATA)
        result = parser.parse(raw)
        expected = hashlib.sha256(
            f"{TEST_UUID}:{TEST_MAJOR}:{TEST_MINOR}".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_length(self, parser):
        raw = make_raw(manufacturer_data=ALTBEACON_DATA)
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)  # must be valid hex

    def test_same_beacon_same_hash(self, parser):
        """Same UUID/major/minor from different MACs => same hash."""
        raw1 = make_raw(manufacturer_data=ALTBEACON_DATA, mac_address="11:22:33:44:55:66")
        raw2 = make_raw(manufacturer_data=ALTBEACON_DATA, mac_address="AA:BB:CC:DD:EE:FF")
        r1 = parser.parse(raw1)
        r2 = parser.parse(raw2)
        assert r1.identifier_hash == r2.identifier_hash


class TestAltBeaconDifferentCompanyIDs:
    def test_any_company_id_with_beac_code(self, parser):
        """AltBeacon works with any company ID as long as beacon code is 0xBEAC."""
        for cid in [0x0118, 0x004C, 0x0006, 0xFFFF, 0x0001]:
            data = build_altbeacon_data(company_id=cid)
            raw = make_raw(manufacturer_data=data)
            result = parser.parse(raw)
            assert result is not None, f"Failed for company_id=0x{cid:04X}"
            assert result.parser_name == "altbeacon"


class TestAltBeaconMalformed:
    def test_returns_none_no_manufacturer_data(self, parser):
        raw = make_raw(manufacturer_data=None)
        assert parser.parse(raw) is None

    def test_returns_none_too_short(self, parser):
        raw = make_raw(manufacturer_data=ALTBEACON_DATA[:20])
        assert parser.parse(raw) is None

    def test_returns_none_wrong_beacon_code(self, parser):
        """Wrong beacon code (not 0xBEAC) should return None."""
        bad_data = build_altbeacon_data(beacon_code=b"\xAB\xCD")
        raw = make_raw(manufacturer_data=bad_data)
        assert parser.parse(raw) is None

    def test_returns_none_empty_data(self, parser):
        raw = make_raw(manufacturer_data=b"")
        assert parser.parse(raw) is None

    def test_returns_none_just_company_id(self, parser):
        raw = make_raw(manufacturer_data=b"\x18\x01")
        assert parser.parse(raw) is None


class TestAltBeaconRegistration:
    def test_registered_as_plugin(self):
        from adwatch.registry import ParserRegistry
        reg = ParserRegistry()

        from adwatch.plugins.altbeacon import AltBeaconParser
        reg.register(
            name="altbeacon",
            description="AltBeacon",
            version="1.0",
            core=False,
            instance=AltBeaconParser(),
        )
        info = reg.get_by_name("altbeacon")
        assert info is not None
        assert info.core is False
        assert info.name == "altbeacon"
