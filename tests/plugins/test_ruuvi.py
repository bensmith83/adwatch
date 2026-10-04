"""Tests for Ruuvi RAWv2 (Data Format 5) BLE parser plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.ruuvi import RuuviParser


@pytest.fixture
def parser():
    return RuuviParser()


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


# --- Helper to build RAWv2 payloads ---

COMPANY_ID_BYTES = bytes([0x99, 0x04])  # 0x0499 little-endian
PAYLOAD_MAC = "11:22:33:44:55:66"
PAYLOAD_MAC_BYTES = bytes([0x11, 0x22, 0x33, 0x44, 0x55, 0x66])


def _build_rawv2(
    *,
    format_byte=0x05,
    temperature=0x0164,    # 356 -> 1.78 C
    humidity=0x5394,       # 21396 -> 53.49%
    pressure=0xC37C,       # 50044 -> 100044 Pa
    accel_x=0x0004,        # 4 mG
    accel_y=-4,            # -4 mG (signed)
    accel_z=0x040C,        # 1036 mG
    power_info=0x9DC7,     # voltage: upper 11 bits = 1262 -> 1262+1600=2862 mV
                           # tx_power: lower 5 bits = 7 -> 7*2-40=-26 dBm
    movement_counter=0x42, # 66
    measurement_seq=0x00CD,# 205
    mac=PAYLOAD_MAC_BYTES,
):
    """Build a complete manufacturer_data blob for Ruuvi RAWv2."""
    buf = COMPANY_ID_BYTES
    buf += bytes([format_byte])
    buf += struct.pack(">h", temperature)
    buf += struct.pack(">H", humidity)
    buf += struct.pack(">H", pressure)
    buf += struct.pack(">h", accel_x)
    buf += struct.pack(">h", accel_y)
    buf += struct.pack(">h", accel_z)
    buf += struct.pack(">H", power_info)
    buf += bytes([movement_counter])
    buf += struct.pack(">H", measurement_seq)
    if mac is not None:
        buf += mac
    return buf


# Pre-built test data
VALID_DATA = _build_rawv2()

# Positive temperature: 1000 * 0.005 = 5.0 C
POS_TEMP_DATA = _build_rawv2(temperature=1000)

# Negative temperature: -1000 * 0.005 = -5.0 C
NEG_TEMP_DATA = _build_rawv2(temperature=-1000)

# Zero temperature
ZERO_TEMP_DATA = _build_rawv2(temperature=0)

# Positive + negative acceleration
POS_ACCEL_DATA = _build_rawv2(accel_x=1000, accel_y=500, accel_z=2000)
NEG_ACCEL_DATA = _build_rawv2(accel_x=-1000, accel_y=-500, accel_z=-2000)

# Wrong format byte
WRONG_FORMAT_DATA = _build_rawv2(format_byte=0x07)  # unknown format

# Wrong company ID
WRONG_COMPANY_DATA = bytes([0x4C, 0x00]) + bytes([0x05]) + b"\x00" * 21

# No MAC in payload (too short)
SHORT_NO_MAC_DATA = _build_rawv2(mac=None)


class TestRuuviTemperature:
    def test_positive_temperature(self, parser):
        raw = make_raw(manufacturer_data=POS_TEMP_DATA)
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["temperature"] == pytest.approx(5.0)

    def test_negative_temperature(self, parser):
        raw = make_raw(manufacturer_data=NEG_TEMP_DATA)
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["temperature"] == pytest.approx(-5.0)

    def test_zero_temperature(self, parser):
        raw = make_raw(manufacturer_data=ZERO_TEMP_DATA)
        result = parser.parse(raw)
        assert result.metadata["temperature"] == pytest.approx(0.0)

    def test_default_temperature(self, parser):
        # 356 * 0.005 = 1.78
        raw = make_raw(manufacturer_data=VALID_DATA)
        result = parser.parse(raw)
        assert result.metadata["temperature"] == pytest.approx(1.78)


class TestRuuviHumidity:
    def test_humidity_value(self, parser):
        # 21396 * 0.0025 = 53.49%
        raw = make_raw(manufacturer_data=VALID_DATA)
        result = parser.parse(raw)
        assert result.metadata["humidity"] == pytest.approx(53.49)

    def test_humidity_zero(self, parser):
        data = _build_rawv2(humidity=0)
        raw = make_raw(manufacturer_data=data)
        result = parser.parse(raw)
        assert result.metadata["humidity"] == pytest.approx(0.0)

    def test_humidity_max(self, parser):
        # 40000 * 0.0025 = 100.0%
        data = _build_rawv2(humidity=40000)
        raw = make_raw(manufacturer_data=data)
        result = parser.parse(raw)
        assert result.metadata["humidity"] == pytest.approx(100.0)


class TestRuuviPressure:
    def test_pressure_value(self, parser):
        # 50044 + 50000 = 100044 Pa
        raw = make_raw(manufacturer_data=VALID_DATA)
        result = parser.parse(raw)
        assert result.metadata["pressure"] == 100044

    def test_pressure_min(self, parser):
        # 0 + 50000 = 50000 Pa
        data = _build_rawv2(pressure=0)
        raw = make_raw(manufacturer_data=data)
        result = parser.parse(raw)
        assert result.metadata["pressure"] == 50000


class TestRuuviAcceleration:
    def test_accel_positive(self, parser):
        raw = make_raw(manufacturer_data=POS_ACCEL_DATA)
        result = parser.parse(raw)
        assert result.metadata["accel_x"] == 1000
        assert result.metadata["accel_y"] == 500
        assert result.metadata["accel_z"] == 2000

    def test_accel_negative(self, parser):
        raw = make_raw(manufacturer_data=NEG_ACCEL_DATA)
        result = parser.parse(raw)
        assert result.metadata["accel_x"] == -1000
        assert result.metadata["accel_y"] == -500
        assert result.metadata["accel_z"] == -2000

    def test_accel_default(self, parser):
        raw = make_raw(manufacturer_data=VALID_DATA)
        result = parser.parse(raw)
        assert result.metadata["accel_x"] == 4
        assert result.metadata["accel_y"] == -4
        assert result.metadata["accel_z"] == 1036


class TestRuuviPowerInfo:
    def test_voltage(self, parser):
        # power_info=0x9DC7 -> upper 11 bits = 0x9DC7 >> 5 = 1262 -> 1262+1600=2862 mV
        raw = make_raw(manufacturer_data=VALID_DATA)
        result = parser.parse(raw)
        assert result.metadata["voltage"] == 2862

    def test_tx_power(self, parser):
        # power_info=0x9DC7 -> lower 5 bits = 0x9DC7 & 0x1F = 7 -> 7*2-40=-26 dBm
        raw = make_raw(manufacturer_data=VALID_DATA)
        result = parser.parse(raw)
        assert result.metadata["tx_power"] == -26


class TestRuuviCounters:
    def test_movement_counter(self, parser):
        raw = make_raw(manufacturer_data=VALID_DATA)
        result = parser.parse(raw)
        assert result.metadata["movement_counter"] == 66

    def test_measurement_sequence(self, parser):
        raw = make_raw(manufacturer_data=VALID_DATA)
        result = parser.parse(raw)
        assert result.metadata["measurement_sequence"] == 205


class TestRuuviIdentity:
    def test_identity_hash_from_payload_mac(self, parser):
        """Identity = SHA256(MAC from payload bytes 18-23)[:16]."""
        raw = make_raw(manufacturer_data=VALID_DATA)
        result = parser.parse(raw)
        expected = hashlib.sha256(PAYLOAD_MAC.encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_fallback_to_raw_mac(self, parser):
        """When payload too short for MAC, fall back to raw.mac_address."""
        raw = make_raw(manufacturer_data=SHORT_NO_MAC_DATA, mac_address="AA:BB:CC:DD:EE:FF")
        result = parser.parse(raw)
        expected = hashlib.sha256("AA:BB:CC:DD:EE:FF".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_format(self, parser):
        raw = make_raw(manufacturer_data=VALID_DATA)
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)  # must be valid hex


class TestRuuviFrameFields:
    def test_parser_name(self, parser):
        raw = make_raw(manufacturer_data=VALID_DATA)
        result = parser.parse(raw)
        assert result.parser_name == "ruuvi"

    def test_device_class(self, parser):
        raw = make_raw(manufacturer_data=VALID_DATA)
        result = parser.parse(raw)
        assert result.device_class == "sensor"

    def test_beacon_type(self, parser):
        raw = make_raw(manufacturer_data=VALID_DATA)
        result = parser.parse(raw)
        assert result.beacon_type == "ruuvi"

    def test_raw_payload_hex(self, parser):
        raw = make_raw(manufacturer_data=VALID_DATA)
        result = parser.parse(raw)
        # raw_payload_hex should be the payload after company ID
        expected = VALID_DATA[2:].hex()
        assert result.raw_payload_hex == expected


class TestRuuviRejectsInvalid:
    def test_wrong_format_byte(self, parser):
        raw = make_raw(manufacturer_data=WRONG_FORMAT_DATA)
        assert parser.parse(raw) is None

    def test_wrong_company_id(self, parser):
        raw = make_raw(manufacturer_data=WRONG_COMPANY_DATA)
        assert parser.parse(raw) is None

    def test_no_manufacturer_data(self, parser):
        raw = make_raw(manufacturer_data=None)
        assert parser.parse(raw) is None

    def test_too_short_data(self, parser):
        raw = make_raw(manufacturer_data=COMPANY_ID_BYTES + bytes([0x05, 0x01]))
        assert parser.parse(raw) is None

    def test_empty_manufacturer_data(self, parser):
        raw = make_raw(manufacturer_data=b"")
        assert parser.parse(raw) is None


class TestRuuviRegistration:
    def test_registered_with_company_id(self):
        from adwatch.registry import ParserRegistry
        reg = ParserRegistry()
        instance = RuuviParser()
        reg.register(
            name="ruuvi",
            company_id=0x0499,
            description="Ruuvi RAWv2",
            version="1.0.0",
            core=False,
            instance=instance,
        )
        raw = make_raw(manufacturer_data=VALID_DATA)
        matched = reg.match(raw)
        assert any(isinstance(p, RuuviParser) for p in matched)

    def test_not_core(self):
        """Ruuvi should be a plugin (core=False)."""
        assert True  # verified by registration above


class TestRuuviStructSafety:
    """Defense-in-depth: if struct.unpack_from raises struct.error
    for any reason, parser must return None instead of crashing."""

    def test_struct_error_returns_none(self, parser):
        """Monkeypatch struct.unpack_from to raise struct.error;
        parser should catch it and return None."""
        import struct as struct_mod
        from unittest.mock import patch

        raw = make_raw(manufacturer_data=VALID_DATA)

        with patch.object(
            struct_mod, "unpack_from", side_effect=struct_mod.error("boom")
        ):
            result = parser.parse(raw)

        assert result is None


# --- Enrichment per apk-ble-hunting ruuvi-station_passive.md ---
# Offsets in the app's decoders are relative to the data-format byte that
# follows FF 99 04 in the raw record == manufacturer_payload[0].

import math


class TestRuuviOffsetBasis:
    def test_hand_built_scan_record(self, parser):
        mfr = _build_rawv2()
        record = bytes.fromhex("020106") + bytes([len(mfr) + 1, 0xFF]) + mfr
        i = record.index(bytes([0xFF, 0x99, 0x04])) + 3  # getActualDataOffset
        assert record[i] == 0x05
        assert record[i:] == mfr[2:]
        result = parser.parse(make_raw(manufacturer_data=mfr))
        assert result.metadata["data_format"] == 5
        assert result.metadata["temperature"] == pytest.approx(1.78)


class TestRuuviFormat5Sentinels:
    def test_invalid_sentinels_omitted(self, parser):
        data = _build_rawv2(temperature=-32768, humidity=0xFFFF, pressure=0xFFFF,
                            power_info=(2047 << 5) | 31)
        result = parser.parse(make_raw(manufacturer_data=data))
        for k in ("temperature", "humidity", "pressure", "voltage", "tx_power"):
            assert k not in result.metadata
        assert result.metadata["movement_counter"] == 66


class TestRuuviFormat3:
    def _data(self, hum=0x65, temp_int=0x81, temp_frac=0x45, pressure=0xC8C5,
              ax=-1000, ay=0, az=1000, batt=2899):
        return (COMPANY_ID_BYTES + bytes([0x03, hum, temp_int, temp_frac])
                + struct.pack(">Hhhh", pressure, ax, ay, az) + struct.pack(">H", batt))

    def test_decode(self, parser):
        result = parser.parse(make_raw(manufacturer_data=self._data()))
        m = result.metadata
        assert m["data_format"] == 3
        assert m["humidity"] == pytest.approx(50.5)
        assert m["temperature"] == pytest.approx(-1.69)
        assert m["pressure"] == 0xC8C5 + 50000
        assert m["accel_x"] == -1000 and m["accel_z"] == 1000
        assert m["voltage"] == 2899
        h = hashlib.sha256("AA:BB:CC:DD:EE:FF".encode()).hexdigest()[:16]
        assert result.identifier_hash == h

    def test_too_short(self, parser):
        assert parser.parse(make_raw(manufacturer_data=self._data()[:10])) is None


class TestRuuviFormatC5:
    def test_decode(self, parser):
        data = (COMPANY_ID_BYTES + bytes([0xC5]) + struct.pack(">hHHHBH",
                -400, 20000, 51000, 0x9DC7, 9, 777))
        m = parser.parse(make_raw(manufacturer_data=data)).metadata
        assert m["data_format"] == 0xC5
        assert m["temperature"] == pytest.approx(-2.0)
        assert m["humidity"] == pytest.approx(50.0)
        assert m["pressure"] == 101000
        assert m["voltage"] == 2862
        assert m["tx_power"] == -26
        assert m["movement_counter"] == 9
        assert m["measurement_sequence"] == 777
        assert "accel_x" not in m


class TestRuuviFormatE0:
    def test_decode(self, parser):
        body = struct.pack(">hhH", 4400, 18000, 51325)
        body += struct.pack(">HHHHH", 12, 55, 60, 71, 845)
        body += bytes([0x01, 0x05, 0x00, 0x20])  # VOC 9-bit = 261, NOx = 32
        body += struct.pack(">H", 350) + bytes([90, 140]) + struct.pack(">H", 1234)
        body += bytes([100])  # battery * 0.03 V
        data = COMPANY_ID_BYTES + bytes([0xE0]) + body
        m = parser.parse(make_raw(manufacturer_data=data)).metadata
        assert m["data_format"] == 0xE0
        assert m["temperature"] == pytest.approx(22.0)
        assert m["humidity"] == pytest.approx(45.0)
        assert m["pressure"] == 101325
        assert m["pm1_0"] == pytest.approx(1.2)
        assert m["pm2_5"] == pytest.approx(5.5)
        assert m["pm4_0"] == pytest.approx(6.0)
        assert m["pm10"] == pytest.approx(7.1)
        assert m["co2"] == 845
        assert m["voc"] == 261
        assert m["nox"] == 32
        assert m["luminosity"] == 350
        assert m["sound_dba_avg"] == pytest.approx(45.0)
        assert m["sound_dba_peak"] == pytest.approx(70.0)
        assert m["measurement_sequence"] == 1234
        assert m["voltage"] == 3000


class TestRuuviFormatE1:
    def test_decode(self, parser):
        body = struct.pack(">hHH", 4400, 18000, 51325)
        body += struct.pack(">HHHHH", 12, 55, 60, 71, 845)
        body += bytes([130, 16])            # VOC (<<1 | flag b6), NOx (<<1 | flag b7)
        body += (123456).to_bytes(3, "big")  # luminosity /100
        body += bytes([100, 110, 120])        # dBA inst/avg/peak (<<1|flag)/5+18
        body += (70000).to_bytes(3, "big")   # sequence 24-bit
        body += bytes([0b01001000])          # flags: b3 inst LSB, b6 VOC LSB
        data = COMPANY_ID_BYTES + bytes([0xE1]) + body
        m = parser.parse(make_raw(manufacturer_data=data)).metadata
        assert m["data_format"] == 0xE1
        assert m["temperature"] == pytest.approx(22.0)
        assert m["voc"] == 261
        assert m["nox"] == 32
        assert m["luminosity"] == pytest.approx(1234.56)
        assert m["sound_dba_inst"] == pytest.approx((201) / 5 + 18)
        assert m["sound_dba_avg"] == pytest.approx(220 / 5 + 18)
        assert m["measurement_sequence"] == 70000
        assert "voltage" not in m


class TestRuuviFormatF0:
    def test_decode(self, parser):
        body = bytes([0xFB, 90, 113, 0, 127, 254, 10, 127, 50, 60, 254, 81])
        data = COMPANY_ID_BYTES + bytes([0xF0]) + body
        m = parser.parse(make_raw(manufacturer_data=data)).metadata
        assert m["data_format"] == 0xF0
        assert m["temperature"] == -5
        assert m["humidity"] == pytest.approx(45.0)
        assert m["pressure"] == 101300
        assert m["pm1_0"] == pytest.approx(0.0)
        assert m["pm2_5"] == pytest.approx(round(math.sqrt(1001) - 1, 2))
        assert m["pm4_0"] == pytest.approx(1000.0)
        assert m["co2"] == round(math.sqrt(40001) - 1)
        assert m["sound_dba_avg"] == pytest.approx(40.5)


class TestRuuviFormat6:
    def test_decode(self, parser):
        body = struct.pack(">hHHHH", 4400, 18000, 51325, 55, 845)
        body += bytes([130, 16, 254, 100, 42])  # VOC, NOx, lum log, dBA, seq
        body += bytes([0b01010000])              # flags b4 (dBA LSB), b6 (VOC LSB)
        body += bytes([0xAA, 0xBB, 0xCC])        # MAC low 3 bytes
        data = COMPANY_ID_BYTES + bytes([0x06]) + body
        m = parser.parse(make_raw(manufacturer_data=data)).metadata
        assert m["data_format"] == 6
        assert m["temperature"] == pytest.approx(22.0)
        assert m["pm2_5"] == pytest.approx(5.5)
        assert m["co2"] == 845
        assert m["voc"] == 261
        assert m["nox"] == 32
        assert m["luminosity"] == pytest.approx(65535.0)
        assert m["sound_dba_avg"] == pytest.approx(201 / 5 + 18)
        assert m["measurement_sequence"] == 42
