"""Tests for Google Find My Device Network BLE parser plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.google_fmd import GoogleFMDParser


@pytest.fixture
def parser():
    return GoogleFMDParser()


FMDN_UUID = "0000fe2c-0000-1000-8000-00805f9b34fb"
GOOGLE_COMPANY_ID_BYTES = bytes([0xE0, 0x00])  # 0x00E0 little-endian


def make_raw(service_data=None, manufacturer_data=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-06T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        service_uuids=[],
        local_name=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        service_data=service_data,
        manufacturer_data=manufacturer_data,
        **defaults,
    )


# --- Test data builders ---

def _build_fmdn_service_data(frame_type=0x01, eid=None, hashed_flags=None):
    """Build service data payload for FMDN frame.

    Byte 0: frame type (0x01 = FMDN, 0x00 = UTP)
    Bytes 1-20: 20-byte EID
    Byte 21 (optional): hashed flags
    """
    if eid is None:
        eid = bytes(range(20))  # 0x00..0x13
    data = bytes([frame_type]) + eid
    if hashed_flags is not None:
        data += bytes([hashed_flags])
    return data


def _build_manufacturer_data(device_type=0x02, tx_power=-10, extra=b""):
    """Build manufacturer data for Google FMD.

    Company ID (2 bytes LE) + device_type (1) + tx_power (1, signed) + extra
    """
    payload = bytes([device_type]) + tx_power.to_bytes(1, "big", signed=True) + extra
    return GOOGLE_COMPANY_ID_BYTES + payload


# --- Pre-built data ---

FMDN_EID = bytes(range(20))  # 20-byte ephemeral identifier
FMDN_FRAME = _build_fmdn_service_data(frame_type=0x01, eid=FMDN_EID)
UTP_FRAME = _build_fmdn_service_data(frame_type=0x00, eid=FMDN_EID)
FMDN_WITH_FLAGS = _build_fmdn_service_data(frame_type=0x01, eid=FMDN_EID, hashed_flags=0xAB)
TRACKER_MFDATA = _build_manufacturer_data(device_type=0x02, tx_power=-10)
PHONE_MFDATA = _build_manufacturer_data(device_type=0x01, tx_power=-5)
HEADPHONES_MFDATA = _build_manufacturer_data(device_type=0x03, tx_power=-15)
ACCESSORY_MFDATA = _build_manufacturer_data(device_type=0x04, tx_power=-20)
WRONG_COMPANY_DATA = bytes([0x4C, 0x00]) + b"\x00" * 5  # Apple company ID


class TestFMDNFrame:
    def test_parse_fmdn_frame(self, parser):
        raw = make_raw(service_data={FMDN_UUID: FMDN_FRAME})
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_frame_type_fmdn(self, parser):
        raw = make_raw(service_data={FMDN_UUID: FMDN_FRAME})
        result = parser.parse(raw)
        assert result.metadata["frame_type"] == 0x01

    def test_eid_as_hex(self, parser):
        raw = make_raw(service_data={FMDN_UUID: FMDN_FRAME})
        result = parser.parse(raw)
        assert result.metadata["eid"] == FMDN_EID.hex()

    def test_protocol_version(self, parser):
        raw = make_raw(service_data={FMDN_UUID: FMDN_FRAME})
        result = parser.parse(raw)
        assert result.metadata["protocol_version"] == 0x01

    def test_hashed_flags_present(self, parser):
        raw = make_raw(service_data={FMDN_UUID: FMDN_WITH_FLAGS})
        result = parser.parse(raw)
        assert result.metadata["hashed_flags"] == 0xAB

    def test_hashed_flags_absent(self, parser):
        """When no hashed flags byte, metadata should not include it or be None."""
        raw = make_raw(service_data={FMDN_UUID: FMDN_FRAME})
        result = parser.parse(raw)
        assert result.metadata.get("hashed_flags") is None


class TestUTPFrame:
    def test_parse_utp_frame(self, parser):
        raw = make_raw(service_data={FMDN_UUID: UTP_FRAME})
        result = parser.parse(raw)
        assert result is not None

    def test_utp_frame_type(self, parser):
        raw = make_raw(service_data={FMDN_UUID: UTP_FRAME})
        result = parser.parse(raw)
        assert result.metadata["frame_type"] == 0x00

    def test_utp_eid(self, parser):
        raw = make_raw(service_data={FMDN_UUID: UTP_FRAME})
        result = parser.parse(raw)
        assert result.metadata["eid"] == FMDN_EID.hex()


class TestManufacturerData:
    def test_parse_tracker(self, parser):
        raw = make_raw(manufacturer_data=TRACKER_MFDATA)
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["device_type"] == "tracker"

    def test_parse_phone(self, parser):
        raw = make_raw(manufacturer_data=PHONE_MFDATA)
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["device_type"] == "phone"

    def test_parse_headphones(self, parser):
        raw = make_raw(manufacturer_data=HEADPHONES_MFDATA)
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["device_type"] == "headphones"

    def test_parse_accessory(self, parser):
        raw = make_raw(manufacturer_data=ACCESSORY_MFDATA)
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["device_type"] == "accessory"

    def test_tx_power(self, parser):
        raw = make_raw(manufacturer_data=TRACKER_MFDATA)
        result = parser.parse(raw)
        assert result.metadata["tx_power"] == -10

    def test_tx_power_positive(self, parser):
        data = _build_manufacturer_data(device_type=0x02, tx_power=4)
        raw = make_raw(manufacturer_data=data)
        result = parser.parse(raw)
        assert result.metadata["tx_power"] == 4

    def test_unknown_device_type(self, parser):
        data = _build_manufacturer_data(device_type=0xFF, tx_power=0)
        raw = make_raw(manufacturer_data=data)
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["device_type"] == "unknown"


class TestServiceDataPriority:
    def test_service_data_preferred_over_manufacturer(self, parser):
        """When both service_data and manufacturer_data are present, parse service_data."""
        raw = make_raw(
            service_data={FMDN_UUID: FMDN_FRAME},
            manufacturer_data=TRACKER_MFDATA,
        )
        result = parser.parse(raw)
        assert result is not None
        # Should have EID from service data, not device_type from manufacturer
        assert "eid" in result.metadata
        assert result.metadata["frame_type"] == 0x01


class TestFrameFields:
    def test_parser_name_service_data(self, parser):
        raw = make_raw(service_data={FMDN_UUID: FMDN_FRAME})
        result = parser.parse(raw)
        assert result.parser_name == "google_fmd"

    def test_parser_name_manufacturer_data(self, parser):
        raw = make_raw(manufacturer_data=TRACKER_MFDATA)
        result = parser.parse(raw)
        assert result.parser_name == "google_fmd"

    def test_beacon_type(self, parser):
        raw = make_raw(service_data={FMDN_UUID: FMDN_FRAME})
        result = parser.parse(raw)
        assert result.beacon_type == "google_fmd"

    def test_device_class_service_data(self, parser):
        raw = make_raw(service_data={FMDN_UUID: FMDN_FRAME})
        result = parser.parse(raw)
        assert result.device_class == "tracker"

    def test_device_class_manufacturer_data(self, parser):
        raw = make_raw(manufacturer_data=TRACKER_MFDATA)
        result = parser.parse(raw)
        assert result.device_class == "tracker"

    def test_raw_payload_hex_service_data(self, parser):
        raw = make_raw(service_data={FMDN_UUID: FMDN_FRAME})
        result = parser.parse(raw)
        assert result.raw_payload_hex == FMDN_FRAME.hex()

    def test_raw_payload_hex_manufacturer_data(self, parser):
        raw = make_raw(manufacturer_data=TRACKER_MFDATA)
        result = parser.parse(raw)
        expected = TRACKER_MFDATA[2:].hex()  # strip company ID
        assert result.raw_payload_hex == expected


class TestIdentity:
    def test_identity_hash_from_mac(self, parser):
        raw = make_raw(service_data={FMDN_UUID: FMDN_FRAME})
        result = parser.parse(raw)
        expected = hashlib.sha256("AA:BB:CC:DD:EE:FF".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_length(self, parser):
        raw = make_raw(service_data={FMDN_UUID: FMDN_FRAME})
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16

    def test_identity_hash_valid_hex(self, parser):
        raw = make_raw(service_data={FMDN_UUID: FMDN_FRAME})
        result = parser.parse(raw)
        int(result.identifier_hash, 16)  # must be valid hex

    def test_identity_hash_same_for_manufacturer_data(self, parser):
        raw = make_raw(manufacturer_data=TRACKER_MFDATA)
        result = parser.parse(raw)
        expected = hashlib.sha256("AA:BB:CC:DD:EE:FF".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected


class TestRejectsInvalid:
    def test_no_data(self, parser):
        raw = make_raw(service_data=None, manufacturer_data=None)
        assert parser.parse(raw) is None

    def test_empty_service_data(self, parser):
        raw = make_raw(service_data={FMDN_UUID: b""})
        assert parser.parse(raw) is None

    def test_wrong_uuid(self, parser):
        raw = make_raw(service_data={"0000abcd-0000-1000-8000-00805f9b34fb": FMDN_FRAME})
        assert parser.parse(raw) is None

    def test_wrong_company_id(self, parser):
        raw = make_raw(manufacturer_data=WRONG_COMPANY_DATA)
        assert parser.parse(raw) is None

    def test_too_short_service_data(self, parser):
        """Service data needs at least 1 (frame type) + 20 (EID) = 21 bytes."""
        short = bytes([0x01]) + bytes(10)  # only 11 bytes
        raw = make_raw(service_data={FMDN_UUID: short})
        assert parser.parse(raw) is None

    def test_too_short_manufacturer_data(self, parser):
        """Manufacturer data needs company ID + at least device_type + tx_power."""
        short = GOOGLE_COMPANY_ID_BYTES + bytes([0x02])  # only 1 payload byte
        raw = make_raw(manufacturer_data=short)
        assert parser.parse(raw) is None

    def test_empty_manufacturer_data(self, parser):
        raw = make_raw(manufacturer_data=b"")
        assert parser.parse(raw) is None


class TestRegistration:
    def test_registered_with_service_uuid(self):
        from adwatch.registry import ParserRegistry
        reg = ParserRegistry()
        instance = GoogleFMDParser()
        reg.register(
            name="google_fmd",
            service_uuid="0000fe2c-0000-1000-8000-00805f9b34fb",
            company_id=0x00E0,
            description="Google Find My Device Network",
            version="1.0.0",
            core=False,
            instance=instance,
        )
        raw = make_raw(service_data={FMDN_UUID: FMDN_FRAME})
        matched = reg.match(raw)
        assert any(isinstance(p, GoogleFMDParser) for p in matched)

    def test_registered_with_company_id(self):
        from adwatch.registry import ParserRegistry
        reg = ParserRegistry()
        instance = GoogleFMDParser()
        reg.register(
            name="google_fmd",
            service_uuid="0000fe2c-0000-1000-8000-00805f9b34fb",
            company_id=0x00E0,
            description="Google Find My Device Network",
            version="1.0.0",
            core=False,
            instance=instance,
        )
        raw = make_raw(manufacturer_data=TRACKER_MFDATA)
        matched = reg.match(raw)
        assert any(isinstance(p, GoogleFMDParser) for p in matched)
