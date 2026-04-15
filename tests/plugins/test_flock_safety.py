"""Tests for Flock Safety surveillance camera plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.flock_safety import FlockSafetyParser, FLOCK_BLE_OUIS


@pytest.fixture
def parser():
    return FlockSafetyParser()


def make_raw(
    manufacturer_data=None,
    service_uuids=None,
    local_name=None,
    mac_address="AA:BB:CC:DD:EE:FF",
    **kwargs,
):
    defaults = dict(
        timestamp="2026-04-10T00:00:00+00:00",
        address_type="public",
        service_data=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        mac_address=mac_address,
        manufacturer_data=manufacturer_data,
        service_uuids=service_uuids or [],
        local_name=local_name,
        **defaults,
    )


# Company ID 0x09C8 in little-endian = bytes [0xC8, 0x09] + payload
XUNTONG_COMPANY_ID = 0x09C8
# Example manufacturer data: company_id LE bytes + serial-like payload
FLOCK_MFR_DATA = bytes([0xC8, 0x09]) + b"TN72023022000771"


class TestFlockSafetyBasicParsing:
    def test_parse_by_company_id(self, parser):
        raw = make_raw(manufacturer_data=FLOCK_MFR_DATA)
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(manufacturer_data=FLOCK_MFR_DATA)
        result = parser.parse(raw)
        assert result.parser_name == "flock_safety"

    def test_beacon_type(self, parser):
        raw = make_raw(manufacturer_data=FLOCK_MFR_DATA)
        result = parser.parse(raw)
        assert result.beacon_type == "flock_safety"

    def test_device_class(self, parser):
        raw = make_raw(manufacturer_data=FLOCK_MFR_DATA)
        result = parser.parse(raw)
        assert result.device_class == "surveillance"

    def test_raw_payload_hex(self, parser):
        raw = make_raw(manufacturer_data=FLOCK_MFR_DATA)
        result = parser.parse(raw)
        assert result.raw_payload_hex == FLOCK_MFR_DATA.hex()


class TestFlockSafetyDeviceNameDetection:
    def test_fs_ext_battery_name(self, parser):
        raw = make_raw(
            local_name="FS Ext Battery",
            manufacturer_data=FLOCK_MFR_DATA,
        )
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["device_type"] == "ext_battery"

    def test_penguin_name(self, parser):
        raw = make_raw(
            local_name="Penguin-1234567890",
            manufacturer_data=FLOCK_MFR_DATA,
        )
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["device_type"] == "penguin"

    def test_pigvision_name(self, parser):
        raw = make_raw(
            local_name="Pigvision",
            manufacturer_data=FLOCK_MFR_DATA,
        )
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["device_type"] == "pigvision"

    def test_generic_flock_name(self, parser):
        """Name containing 'Flock' should match the generic flock type."""
        raw = make_raw(
            local_name="FlockCam-ABC123",
            manufacturer_data=FLOCK_MFR_DATA,
        )
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["device_type"] == "flock"

    def test_unknown_name_with_company_id(self, parser):
        """Device with XUNTONG company ID but no recognized name."""
        raw = make_raw(manufacturer_data=FLOCK_MFR_DATA)
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["device_type"] == "unknown"


class TestFlockSafetyOUIDetection:
    def test_known_ble_oui_with_company_id(self, parser):
        """Known Flock BLE OUI should be flagged in metadata."""
        raw = make_raw(
            mac_address="EC:1B:BD:AA:BB:CC",
            manufacturer_data=FLOCK_MFR_DATA,
        )
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["known_oui"] is True

    def test_unknown_oui_with_company_id(self, parser):
        """Unknown OUI but valid company ID should still parse."""
        raw = make_raw(
            mac_address="AA:BB:CC:DD:EE:FF",
            manufacturer_data=FLOCK_MFR_DATA,
        )
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["known_oui"] is False

    def test_all_known_ble_ouis(self, parser):
        """All known BLE OUI prefixes should be recognized."""
        expected_ouis = [
            "EC:1B:BD", "58:8E:81", "90:35:EA", "CC:CC:CC",
            "B4:E3:F9", "04:0D:84", "F0:82:C0",
            "1C:34:F1", "38:5B:44", "94:34:69",
            "B4:1E:52",
        ]
        for oui in expected_ouis:
            assert oui in FLOCK_BLE_OUIS, f"{oui} not in FLOCK_BLE_OUIS"


class TestFlockSafetySerialExtraction:
    def test_serial_from_payload(self, parser):
        """Manufacturer payload after company ID contains serial number."""
        raw = make_raw(manufacturer_data=FLOCK_MFR_DATA)
        result = parser.parse(raw)
        assert "payload_hex" in result.metadata

    def test_payload_hex_content(self, parser):
        raw = make_raw(manufacturer_data=FLOCK_MFR_DATA)
        result = parser.parse(raw)
        # Payload hex should be the manufacturer data hex
        assert result.raw_payload_hex == FLOCK_MFR_DATA.hex()


class TestFlockSafetyIdentityHash:
    def test_hash_format(self, parser):
        raw = make_raw(manufacturer_data=FLOCK_MFR_DATA)
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)  # must be valid hex

    def test_hash_uses_mac(self, parser):
        """Different MACs should produce different hashes."""
        raw1 = make_raw(mac_address="EC:1B:BD:00:00:01", manufacturer_data=FLOCK_MFR_DATA)
        raw2 = make_raw(mac_address="EC:1B:BD:00:00:02", manufacturer_data=FLOCK_MFR_DATA)
        r1 = parser.parse(raw1)
        r2 = parser.parse(raw2)
        assert r1.identifier_hash != r2.identifier_hash


class TestFlockSafetyMalformed:
    def test_returns_none_no_manufacturer_data(self, parser):
        raw = make_raw(manufacturer_data=None)
        assert parser.parse(raw) is None

    def test_returns_none_wrong_company_id(self, parser):
        """Non-XUNTONG company ID should not match."""
        wrong_data = bytes([0x4C, 0x00]) + b"\x01\x02\x03"
        raw = make_raw(manufacturer_data=wrong_data)
        assert parser.parse(raw) is None

    def test_returns_none_too_short(self, parser):
        """Data shorter than 2 bytes (company ID only) should not match."""
        raw = make_raw(manufacturer_data=bytes([0xC8, 0x09]))
        assert parser.parse(raw) is None


class TestFlockSafetyStorageSchema:
    def test_no_storage(self, parser):
        assert parser.storage_schema() is None
