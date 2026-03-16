"""Tests for EnOcean BLE energy-harvesting sensor plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

# RED phase — this import will fail until the plugin exists
from adwatch.plugins.enocean import EnOceanParser

ENOCEAN_COMPANY_ID = 0x03DA


def _make_ad(**kwargs):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "random",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _mfr_data(payload: bytes) -> bytes:
    """Build manufacturer_data with company ID prefix."""
    return struct.pack("<H", ENOCEAN_COMPANY_ID) + payload


class TestEnOceanRegistration:
    def test_match_by_company_id(self):
        """Should match by company_id 0x03DA."""
        registry = ParserRegistry()

        @register_parser(
            name="enocean", company_id=ENOCEAN_COMPANY_ID,
            description="EnOcean", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(EnOceanParser):
            pass

        mfr = _mfr_data(b"\x05\x00\x01")  # minimal payload
        ad = _make_ad(manufacturer_data=mfr)
        assert len(registry.match(ad)) == 1


class TestSTM550B:
    """STM550B multi-sensor module (event type 0x00)."""

    def test_full_parse(self):
        """Parse all STM550B fields: temp, humidity, illumination, accel, magnet."""
        parser = EnOceanParser()
        # Payload: seq=42, type=0x00, temp=2350 (23.50C), humidity=55,
        # illumination=500, accel_x=100, accel_y=-50, accel_z=980, magnet=1
        payload = struct.pack("<BB", 42, 0x00)  # seq, type
        payload += struct.pack("<h", 2350)       # temp int16 LE
        payload += struct.pack("<B", 55)          # humidity uint8
        payload += struct.pack("<H", 500)         # illumination uint16 LE
        payload += struct.pack("<h", 100)         # accel_x
        payload += struct.pack("<h", -50)         # accel_y
        payload += struct.pack("<h", 980)         # accel_z
        payload += struct.pack("<B", 1)           # magnet=closed

        ad = _make_ad(manufacturer_data=_mfr_data(payload))
        result = parser.parse(ad)

        assert result is not None
        assert result.parser_name == "enocean"
        assert result.beacon_type == "enocean"
        assert result.device_class == "sensor"
        assert result.metadata["sensor_module"] == "stm550b"
        assert result.metadata["sequence"] == 42
        assert result.metadata["temperature"] == 23.50
        assert result.metadata["humidity"] == 55
        assert result.metadata["illumination"] == 500
        assert result.metadata["accel_x"] == 100
        assert result.metadata["accel_y"] == -50
        assert result.metadata["accel_z"] == 980
        assert result.metadata["magnet_contact"] is True
        assert result.metadata["authenticated"] is False

    def test_negative_temperature(self):
        """Negative temperature should parse correctly."""
        parser = EnOceanParser()
        payload = struct.pack("<BB", 1, 0x00)
        payload += struct.pack("<h", -550)        # -5.50C
        payload += struct.pack("<B", 80)
        payload += struct.pack("<H", 100)
        payload += struct.pack("<hhh", 0, 0, 0)
        payload += struct.pack("<B", 0)

        ad = _make_ad(manufacturer_data=_mfr_data(payload))
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["temperature"] == -5.50

    def test_with_cmac_signature(self):
        """STM550B with 4-byte CMAC → authenticated=True."""
        parser = EnOceanParser()
        payload = struct.pack("<BB", 10, 0x00)
        payload += struct.pack("<h", 2000)
        payload += struct.pack("<B", 50)
        payload += struct.pack("<H", 300)
        payload += struct.pack("<hhh", 0, 0, 1000)
        payload += struct.pack("<B", 0)
        payload += b"\xDE\xAD\xBE\xEF"  # 4-byte CMAC

        ad = _make_ad(manufacturer_data=_mfr_data(payload))
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["authenticated"] is True
        # Sensor data should still parse correctly
        assert result.metadata["temperature"] == 20.00


class TestEMDCB:
    """EMDCB motion detector (event type 0x01)."""

    def test_motion_detected(self):
        """Parse EMDCB with motion=True."""
        parser = EnOceanParser()
        payload = struct.pack("<BB", 7, 0x01)  # seq=7, type=EMDCB
        payload += struct.pack("<B", 1)         # motion=True
        payload += struct.pack("<H", 850)       # illumination=850 lux

        ad = _make_ad(manufacturer_data=_mfr_data(payload))
        result = parser.parse(ad)

        assert result is not None
        assert result.metadata["sensor_module"] == "emdcb"
        assert result.metadata["sequence"] == 7
        assert result.metadata["motion"] is True
        assert result.metadata["illumination"] == 850
        assert result.metadata["authenticated"] is False

    def test_no_motion(self):
        """Parse EMDCB with motion=False."""
        parser = EnOceanParser()
        payload = struct.pack("<BB", 3, 0x01)
        payload += struct.pack("<B", 0)
        payload += struct.pack("<H", 0)

        ad = _make_ad(manufacturer_data=_mfr_data(payload))
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["motion"] is False

    def test_with_cmac(self):
        """EMDCB with CMAC → authenticated=True."""
        parser = EnOceanParser()
        payload = struct.pack("<BB", 3, 0x01)
        payload += struct.pack("<B", 1)
        payload += struct.pack("<H", 200)
        payload += b"\x01\x02\x03\x04"  # CMAC

        ad = _make_ad(manufacturer_data=_mfr_data(payload))
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["authenticated"] is True


class TestPTM216B:
    """PTM 216B pushbutton (event type 0x02)."""

    def test_button_press(self):
        """Parse PTM216B button event."""
        parser = EnOceanParser()
        # Button byte: bit 0 = press(1)/release(0), bit 1 = rocker A(0)/B(1)
        payload = struct.pack("<BB", 99, 0x02)  # seq=99, type=PTM216B
        payload += struct.pack("<B", 0x01)       # press, rocker A

        ad = _make_ad(manufacturer_data=_mfr_data(payload))
        result = parser.parse(ad)

        assert result is not None
        assert result.metadata["sensor_module"] == "ptm216b"
        assert result.metadata["sequence"] == 99
        assert "button_event" in result.metadata
        assert isinstance(result.metadata["button_event"], str)
        assert result.metadata["authenticated"] is False

    def test_button_release(self):
        """Button release event."""
        parser = EnOceanParser()
        payload = struct.pack("<BB", 5, 0x02)
        payload += struct.pack("<B", 0x00)  # release, rocker A

        ad = _make_ad(manufacturer_data=_mfr_data(payload))
        result = parser.parse(ad)
        assert result is not None
        assert "release" in result.metadata["button_event"].lower()

    def test_rocker_b(self):
        """Rocker B press."""
        parser = EnOceanParser()
        payload = struct.pack("<BB", 5, 0x02)
        payload += struct.pack("<B", 0x03)  # press + rocker B

        ad = _make_ad(manufacturer_data=_mfr_data(payload))
        result = parser.parse(ad)
        assert result is not None
        assert "b" in result.metadata["button_event"].lower()


class TestUnknownModule:
    """Unknown event type should still return a result."""

    def test_unknown_event_type(self):
        parser = EnOceanParser()
        payload = struct.pack("<BB", 1, 0xFF)  # unknown type
        payload += b"\x01\x02\x03"

        ad = _make_ad(manufacturer_data=_mfr_data(payload))
        result = parser.parse(ad)

        assert result is not None
        assert result.metadata["sensor_module"] == "unknown"
        assert result.metadata["sequence"] == 1


class TestEdgeCases:
    """Edge cases and error handling."""

    def test_too_short_data(self):
        """Payload too short (< 2 bytes for seq+type) → None."""
        parser = EnOceanParser()
        payload = b"\x01"  # only 1 byte
        ad = _make_ad(manufacturer_data=_mfr_data(payload))
        result = parser.parse(ad)
        assert result is None

    def test_no_manufacturer_data(self):
        """No manufacturer data → None."""
        parser = EnOceanParser()
        ad = _make_ad(manufacturer_data=None)
        result = parser.parse(ad)
        assert result is None

    def test_identity_hash(self):
        """Identity hash: SHA256('{mac}:enocean')[:16]."""
        parser = EnOceanParser()
        payload = struct.pack("<BB", 1, 0x01)
        payload += struct.pack("<B", 0)
        payload += struct.pack("<H", 0)

        ad = _make_ad(
            manufacturer_data=_mfr_data(payload),
            mac_address="11:22:33:44:55:66",
        )
        result = parser.parse(ad)
        expected = hashlib.sha256("11:22:33:44:55:66:enocean".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected
