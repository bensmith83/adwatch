"""Tests for Rivian vehicle/phone key plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.rivian import RivianParser


RIVIAN_COMPANY_ID = 0x0941

# Real samples from CSV
PHONE_KEY_DATA = bytes.fromhex("41090101061a0363")
VEHICLE_DATA = bytes.fromhex("4109170900")

PHONE_KEY_UUID = "3DB57984-B50C-509B-BCE5-153071780C83"
VEHICLE_UUID = "6F65732A-5F72-6976-3031-7446B3C9CBC9"

MAC = "AA:BB:CC:DD:EE:FF"


@pytest.fixture
def parser():
    return RivianParser()


def make_raw(manufacturer_data=None, service_uuids=None, local_name=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-05T00:00:00+00:00",
        mac_address=MAC,
        address_type="random",
        service_data=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        manufacturer_data=manufacturer_data,
        service_uuids=service_uuids or [],
        local_name=local_name,
        **defaults,
    )


class TestRivianPhoneKeyMode:
    def test_parse_phone_key_returns_result(self, parser):
        raw = make_raw(
            manufacturer_data=PHONE_KEY_DATA,
            service_uuids=[PHONE_KEY_UUID],
            local_name="Rivian Phone Key",
        )
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(manufacturer_data=PHONE_KEY_DATA, local_name="Rivian Phone Key")
        result = parser.parse(raw)
        assert result.parser_name == "rivian"

    def test_beacon_type(self, parser):
        raw = make_raw(manufacturer_data=PHONE_KEY_DATA, local_name="Rivian Phone Key")
        result = parser.parse(raw)
        assert result.beacon_type == "rivian"

    def test_device_class_vehicle_key(self, parser):
        raw = make_raw(manufacturer_data=PHONE_KEY_DATA, local_name="Rivian Phone Key")
        result = parser.parse(raw)
        assert result.device_class == "vehicle_key"

    def test_mode_phone_key(self, parser):
        """Manufacturer data byte 2 = 0x01 → phone_key mode."""
        raw = make_raw(manufacturer_data=PHONE_KEY_DATA, local_name="Rivian Phone Key")
        result = parser.parse(raw)
        assert result.metadata["mode"] == "phone_key"

    def test_identity_hash(self, parser):
        raw = make_raw(manufacturer_data=PHONE_KEY_DATA, local_name="Rivian Phone Key")
        result = parser.parse(raw)
        expected = hashlib.sha256(f"rivian:{MAC}".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_format(self, parser):
        raw = make_raw(manufacturer_data=PHONE_KEY_DATA, local_name="Rivian Phone Key")
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_metadata_device_name(self, parser):
        raw = make_raw(manufacturer_data=PHONE_KEY_DATA, local_name="Rivian Phone Key")
        result = parser.parse(raw)
        assert result.metadata["device_name"] == "Rivian Phone Key"


class TestRivianVehicleMode:
    def test_parse_vehicle_returns_result(self, parser):
        raw = make_raw(
            manufacturer_data=VEHICLE_DATA,
            service_uuids=[VEHICLE_UUID],
            local_name="RIVN",
        )
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_device_class_vehicle(self, parser):
        raw = make_raw(manufacturer_data=VEHICLE_DATA, local_name="RIVN")
        result = parser.parse(raw)
        assert result.device_class == "vehicle"

    def test_mode_vehicle(self, parser):
        """Manufacturer data byte 2 = 0x17 → vehicle mode."""
        raw = make_raw(manufacturer_data=VEHICLE_DATA, local_name="RIVN")
        result = parser.parse(raw)
        assert result.metadata["mode"] == "vehicle"


class TestRivianPassiveMode:
    def test_parse_name_only_rivian_phone_key(self, parser):
        """Should match on local_name 'Rivian Phone Key' alone."""
        raw = make_raw(local_name="Rivian Phone Key")
        result = parser.parse(raw)
        assert result is not None

    def test_parse_name_only_rivn(self, parser):
        """Should match on local_name 'RIVN' alone."""
        raw = make_raw(local_name="RIVN")
        result = parser.parse(raw)
        assert result is not None

    def test_passive_mode(self, parser):
        """Name-only match → passive mode."""
        raw = make_raw(local_name="Rivian Phone Key")
        result = parser.parse(raw)
        assert result.metadata["mode"] == "passive"

    def test_company_id_only_match(self, parser):
        """Should match on company_id 0x0941 alone."""
        raw = make_raw(manufacturer_data=PHONE_KEY_DATA)
        result = parser.parse(raw)
        assert result is not None


class TestRivianIdentity:
    def test_same_mac_same_hash(self, parser):
        """Both modes from same MAC should have same identity hash."""
        r1 = parser.parse(make_raw(manufacturer_data=PHONE_KEY_DATA, local_name="Rivian Phone Key"))
        r2 = parser.parse(make_raw(manufacturer_data=VEHICLE_DATA, local_name="RIVN"))
        assert r1.identifier_hash == r2.identifier_hash

    def test_different_mac_different_hash(self, parser):
        r1 = parser.parse(make_raw(manufacturer_data=PHONE_KEY_DATA, local_name="Rivian Phone Key"))
        r2 = parser.parse(make_raw(
            manufacturer_data=PHONE_KEY_DATA,
            local_name="Rivian Phone Key",
            mac_address="11:22:33:44:55:66",
        ))
        assert r1.identifier_hash != r2.identifier_hash


class TestRivianRejection:
    def test_returns_none_wrong_company_id(self, parser):
        wrong = bytearray(PHONE_KEY_DATA)
        wrong[0] = 0xFF
        wrong[1] = 0xFF
        raw = make_raw(manufacturer_data=bytes(wrong))
        assert parser.parse(raw) is None

    def test_returns_none_no_data_no_name(self, parser):
        raw = make_raw()
        assert parser.parse(raw) is None

    def test_returns_none_unrelated_name(self, parser):
        raw = make_raw(local_name="SomeOtherDevice")
        assert parser.parse(raw) is None
