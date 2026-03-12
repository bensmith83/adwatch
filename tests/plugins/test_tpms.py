"""Tests for TPMS (Tire Pressure Monitoring) plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.tpms import TPMSParser


@pytest.fixture
def parser():
    return TPMSParser()


def make_raw(manufacturer_data=None, local_name=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-06T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        service_data=None,
        service_uuids=[],
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        manufacturer_data=manufacturer_data,
        local_name=local_name,
        **defaults,
    )


# Company ID 0x0001 little-endian = b'\x01\x00'
# Payload: sensor_index=1, battery_raw=150 (3.0V), temp_raw=65 (25C),
#          pressure=23000 (230.00 kPa) LE, checksum=0x0000
COMPANY_ID = b"\x01\x00"
TPMS_PAYLOAD = bytes([0x01, 0x96, 0x41]) + struct.pack("<H", 23000) + bytes([0x00, 0x00])
TPMS_DATA = COMPANY_ID + TPMS_PAYLOAD


class TestTPMSParsing:
    def test_parse_valid_tpms(self, parser):
        raw = make_raw(manufacturer_data=TPMS_DATA, local_name="TPMS1_ABCD")
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(manufacturer_data=TPMS_DATA, local_name="TPMS1_ABCD")
        result = parser.parse(raw)
        assert result.parser_name == "tpms"

    def test_beacon_type(self, parser):
        raw = make_raw(manufacturer_data=TPMS_DATA, local_name="TPMS1_ABCD")
        result = parser.parse(raw)
        assert result.beacon_type == "tpms"

    def test_device_class_sensor(self, parser):
        raw = make_raw(manufacturer_data=TPMS_DATA, local_name="TPMS1_ABCD")
        result = parser.parse(raw)
        assert result.device_class == "sensor"

    def test_sensor_index(self, parser):
        raw = make_raw(manufacturer_data=TPMS_DATA, local_name="TPMS1_ABCD")
        result = parser.parse(raw)
        assert result.metadata["sensor_index"] == 1

    def test_battery_voltage(self, parser):
        raw = make_raw(manufacturer_data=TPMS_DATA, local_name="TPMS1_ABCD")
        result = parser.parse(raw)
        assert result.metadata["battery_voltage"] == pytest.approx(3.0)

    def test_temperature(self, parser):
        raw = make_raw(manufacturer_data=TPMS_DATA, local_name="TPMS1_ABCD")
        result = parser.parse(raw)
        assert result.metadata["temperature_c"] == 25

    def test_pressure_kpa(self, parser):
        raw = make_raw(manufacturer_data=TPMS_DATA, local_name="TPMS1_ABCD")
        result = parser.parse(raw)
        assert result.metadata["pressure_kpa"] == pytest.approx(230.00)

    def test_raw_payload_hex(self, parser):
        raw = make_raw(manufacturer_data=TPMS_DATA, local_name="TPMS1_ABCD")
        result = parser.parse(raw)
        assert result.raw_payload_hex == TPMS_PAYLOAD.hex()


class TestTPMSIdentity:
    def test_identity_hash(self, parser):
        """Identity = SHA256(mac_address + sensor_index)[:16]."""
        raw = make_raw(
            manufacturer_data=TPMS_DATA,
            local_name="TPMS1_ABCD",
            mac_address="11:22:33:44:55:66",
        )
        result = parser.parse(raw)
        expected = hashlib.sha256(
            "11:22:33:44:55:661".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_format(self, parser):
        raw = make_raw(manufacturer_data=TPMS_DATA, local_name="TPMS1_ABCD")
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)  # must be valid hex


class TestTPMSMatching:
    def test_matches_by_local_name_tpms(self, parser):
        """Should parse when local_name starts with TPMS."""
        raw = make_raw(manufacturer_data=TPMS_DATA, local_name="TPMS_sensor")
        result = parser.parse(raw)
        assert result is not None

    def test_matches_by_local_name_br(self, parser):
        """Should parse when local_name starts with BR."""
        raw = make_raw(manufacturer_data=TPMS_DATA, local_name="BR12345")
        result = parser.parse(raw)
        assert result is not None

    def test_matches_by_company_id_only(self, parser):
        """Should parse with company_id=0x0001 even without matching local_name."""
        raw = make_raw(manufacturer_data=TPMS_DATA, local_name=None)
        result = parser.parse(raw)
        assert result is not None


class TestTPMSEdgeCases:
    def test_sensor_index_zero(self, parser):
        payload = bytes([0x00, 0x96, 0x41]) + struct.pack("<H", 23000) + bytes([0x00, 0x00])
        raw = make_raw(manufacturer_data=COMPANY_ID + payload, local_name="TPMS1")
        result = parser.parse(raw)
        assert result.metadata["sensor_index"] == 0

    def test_sensor_index_three(self, parser):
        payload = bytes([0x03, 0x96, 0x41]) + struct.pack("<H", 23000) + bytes([0x00, 0x00])
        raw = make_raw(manufacturer_data=COMPANY_ID + payload, local_name="TPMS1")
        result = parser.parse(raw)
        assert result.metadata["sensor_index"] == 3

    def test_zero_pressure(self, parser):
        payload = bytes([0x00, 0x96, 0x41]) + struct.pack("<H", 0) + bytes([0x00, 0x00])
        raw = make_raw(manufacturer_data=COMPANY_ID + payload, local_name="TPMS1")
        result = parser.parse(raw)
        assert result.metadata["pressure_kpa"] == 0.0

    def test_no_storage(self, parser):
        assert parser.storage_schema() is None

    def test_has_ui(self, parser):
        cfg = parser.ui_config()
        assert cfg is not None
        assert cfg.tab_name == "TPMS"


class TestTPMSMalformed:
    def test_returns_none_no_manufacturer_data(self, parser):
        raw = make_raw(manufacturer_data=None, local_name="TPMS1")
        assert parser.parse(raw) is None

    def test_returns_none_payload_too_short(self, parser):
        """Need at least 5 bytes payload (7 total with company ID)."""
        short = COMPANY_ID + bytes([0x01, 0x96, 0x41, 0x00])  # only 4 payload bytes
        raw = make_raw(manufacturer_data=short, local_name="TPMS1")
        assert parser.parse(raw) is None

    def test_returns_none_manufacturer_data_too_short(self, parser):
        raw = make_raw(manufacturer_data=b"\x01", local_name="TPMS1")
        assert parser.parse(raw) is None

    def test_minimum_valid_payload(self, parser):
        """Exactly 5 payload bytes (through pressure) should work."""
        payload = bytes([0x02, 0x96, 0x41]) + struct.pack("<H", 20000)
        raw = make_raw(manufacturer_data=COMPANY_ID + payload, local_name="TPMS1")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["pressure_kpa"] == pytest.approx(200.00)
