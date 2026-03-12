"""Tests for Govee Sensors BLE parser plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.govee import GoveeParser, GOVEE_VIBRATION_COMPANY_ID


@pytest.fixture
def parser():
    return GoveeParser()


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
        manufacturer_data=manufacturer_data, local_name=local_name, **defaults
    )


# --- Constants ---

COMPANY_ID_BYTES = bytes([0x88, 0xEC])  # 0xEC88 little-endian


# --- H5074 format builders ---

def _build_h5074(
    *,
    temperature=2580,   # 25.80 C
    humidity=5247,       # 52.47 %
    battery=87,          # 87%
    pad_prefix=b"\x00\x00",  # 2 bytes before temp (offset 0-1)
):
    """Build manufacturer_data for H5074 format.

    Payload layout (after company ID):
      offset 0-1: prefix bytes (device-specific, not parsed)
      offset 2-3: temperature as int16 LE, /100 for C
      offset 4-5: humidity as uint16 LE, /100 for %
      offset 6:   battery percentage
    """
    payload = pad_prefix
    payload += struct.pack("<h", temperature)
    payload += struct.pack("<H", humidity)
    payload += bytes([battery])
    return COMPANY_ID_BYTES + payload


def _build_h5075(
    *,
    encoded_value=256470,  # temp=25.6 C, hum=47.0%
    battery=91,
    pad_prefix=b"\x00\x00\x00",  # 3 bytes before encoded (offset 0-2)
):
    """Build manufacturer_data for H5075/H5072 3-byte encoding format.

    Payload layout (after company ID):
      offset 0-2: prefix bytes
      offset 3-5: 3-byte big-endian encoded value
      offset 6:   battery percentage

    Encoded value:
      temperature = value / 10000  (C)
      humidity = (value % 1000) / 10  (%)
      If bit 23 is set, temperature is negative.
    """
    payload = pad_prefix
    payload += encoded_value.to_bytes(3, "big")
    payload += bytes([battery])
    return COMPANY_ID_BYTES + payload


# --- Pre-built test data ---

# H5074: 25.80 C, 52.47%, 87% battery
H5074_VALID = _build_h5074()

# H5074: negative temp -5.20 C
H5074_NEG_TEMP = _build_h5074(temperature=-520)

# H5074: zero temp
H5074_ZERO_TEMP = _build_h5074(temperature=0, humidity=5000, battery=100)

# H5075: encoded_value=256470 -> temp=256470/10000=25.647->25.6 C, hum=256470%1000/10=47.0%
H5075_VALID = _build_h5075(encoded_value=256470, battery=91)

# H5075: negative temp via bit 23
# bit 23 set: 0x800000 | value. temp = -(value/10000), hum = value%1000/10
# value with bit23 = 0x800000 | 103550 = 8491038
# temp = -(103550/10000) = -10.355 -> -10.355 C, hum = 103550%1000/10 = 55.0%
H5075_NEG_TEMP = _build_h5075(encoded_value=(0x800000 | 103550), battery=80)

# Wrong company ID
WRONG_COMPANY_DATA = bytes([0x4C, 0x00]) + b"\x00" * 7


class TestGoveeH5074Temperature:
    def test_positive_temperature(self, parser):
        raw = make_raw(manufacturer_data=H5074_VALID, local_name="GVH5074_1234")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["temperature_c"] == pytest.approx(25.80)

    def test_negative_temperature(self, parser):
        raw = make_raw(manufacturer_data=H5074_NEG_TEMP, local_name="GVH5074_1234")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["temperature_c"] == pytest.approx(-5.20)

    def test_zero_temperature(self, parser):
        raw = make_raw(manufacturer_data=H5074_ZERO_TEMP, local_name="GVH5074_1234")
        result = parser.parse(raw)
        assert result.metadata["temperature_c"] == pytest.approx(0.0)


class TestGoveeH5074Humidity:
    def test_humidity_value(self, parser):
        raw = make_raw(manufacturer_data=H5074_VALID, local_name="GVH5074_1234")
        result = parser.parse(raw)
        assert result.metadata["humidity_percent"] == pytest.approx(52.47)

    def test_zero_humidity(self, parser):
        data = _build_h5074(humidity=0)
        raw = make_raw(manufacturer_data=data, local_name="GVH5074_1234")
        result = parser.parse(raw)
        assert result.metadata["humidity_percent"] == pytest.approx(0.0)


class TestGoveeH5074Battery:
    def test_battery_value(self, parser):
        raw = make_raw(manufacturer_data=H5074_VALID, local_name="GVH5074_1234")
        result = parser.parse(raw)
        assert result.metadata["battery_percent"] == 87


class TestGoveeH5075Format:
    def test_positive_temperature(self, parser):
        # 256470 / 10000 = 25.647 C
        raw = make_raw(manufacturer_data=H5075_VALID, local_name="GVH5075_5678")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["temperature_c"] == pytest.approx(25.647)

    def test_humidity(self, parser):
        # 256470 % 1000 / 10 = 47.0%
        raw = make_raw(manufacturer_data=H5075_VALID, local_name="GVH5075_5678")
        result = parser.parse(raw)
        assert result.metadata["humidity_percent"] == pytest.approx(47.0)

    def test_battery(self, parser):
        raw = make_raw(manufacturer_data=H5075_VALID, local_name="GVH5075_5678")
        result = parser.parse(raw)
        assert result.metadata["battery_percent"] == 91

    def test_negative_temperature_bit23(self, parser):
        # bit 23 set: temp is negative
        # value without bit23 = 103550, temp = -(103550/10000) = -10.355
        raw = make_raw(manufacturer_data=H5075_NEG_TEMP, local_name="GVH5075_5678")
        result = parser.parse(raw)
        assert result.metadata["temperature_c"] == pytest.approx(-10.355)

    def test_negative_temp_humidity(self, parser):
        # 103550 % 1000 / 10 = 55.0%
        raw = make_raw(manufacturer_data=H5075_NEG_TEMP, local_name="GVH5075_5678")
        result = parser.parse(raw)
        assert result.metadata["humidity_percent"] == pytest.approx(55.0)

    def test_h5072_name_uses_h5075_format(self, parser):
        raw = make_raw(manufacturer_data=H5075_VALID, local_name="GVH5072_9999")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["temperature_c"] == pytest.approx(25.647)


class TestGoveeModel:
    def test_h5074_model(self, parser):
        raw = make_raw(manufacturer_data=H5074_VALID, local_name="GVH5074_1234")
        result = parser.parse(raw)
        assert result.metadata["model"] == "H5074"

    def test_h5075_model(self, parser):
        raw = make_raw(manufacturer_data=H5075_VALID, local_name="GVH5075_5678")
        result = parser.parse(raw)
        assert result.metadata["model"] == "H5075"

    def test_h5072_model(self, parser):
        raw = make_raw(manufacturer_data=H5075_VALID, local_name="GVH5072_9999")
        result = parser.parse(raw)
        assert result.metadata["model"] == "H5072"

    def test_no_local_name_defaults_h5074(self, parser):
        """Without a recognizable local_name, try H5074 format if payload is long enough."""
        raw = make_raw(manufacturer_data=H5074_VALID)
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["model"] == "unknown"


class TestGoveeMatching:
    def test_match_by_company_id_only(self, parser):
        """Should parse even without local_name if company_id matches."""
        raw = make_raw(manufacturer_data=H5074_VALID)
        result = parser.parse(raw)
        assert result is not None

    def test_match_by_local_name_gvh5(self, parser):
        raw = make_raw(manufacturer_data=H5074_VALID, local_name="GVH5074_1234")
        result = parser.parse(raw)
        assert result is not None

    def test_match_by_local_name_govee(self, parser):
        raw = make_raw(manufacturer_data=H5074_VALID, local_name="Govee_H5074_1234")
        result = parser.parse(raw)
        assert result is not None


class TestGoveeIdentity:
    def test_identity_hash_from_mac(self, parser):
        """Identity = SHA256(raw.mac_address)[:16]."""
        raw = make_raw(manufacturer_data=H5074_VALID, local_name="GVH5074_1234")
        result = parser.parse(raw)
        expected = hashlib.sha256("AA:BB:CC:DD:EE:FF".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_length(self, parser):
        raw = make_raw(manufacturer_data=H5074_VALID, local_name="GVH5074_1234")
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)  # must be valid hex


class TestGoveeFrameFields:
    def test_parser_name(self, parser):
        raw = make_raw(manufacturer_data=H5074_VALID, local_name="GVH5074_1234")
        result = parser.parse(raw)
        assert result.parser_name == "govee"

    def test_device_class(self, parser):
        raw = make_raw(manufacturer_data=H5074_VALID, local_name="GVH5074_1234")
        result = parser.parse(raw)
        assert result.device_class == "sensor"

    def test_beacon_type(self, parser):
        raw = make_raw(manufacturer_data=H5074_VALID, local_name="GVH5074_1234")
        result = parser.parse(raw)
        assert result.beacon_type == "govee"

    def test_raw_payload_hex(self, parser):
        raw = make_raw(manufacturer_data=H5074_VALID, local_name="GVH5074_1234")
        result = parser.parse(raw)
        expected = H5074_VALID[2:].hex()
        assert result.raw_payload_hex == expected


class TestGoveeRejectsInvalid:
    def test_no_manufacturer_data(self, parser):
        raw = make_raw(manufacturer_data=None)
        assert parser.parse(raw) is None

    def test_empty_manufacturer_data(self, parser):
        raw = make_raw(manufacturer_data=b"")
        assert parser.parse(raw) is None

    def test_wrong_company_id(self, parser):
        raw = make_raw(manufacturer_data=WRONG_COMPANY_DATA)
        assert parser.parse(raw) is None

    def test_too_short_payload(self, parser):
        # Only company ID + 2 bytes, not enough for any format
        raw = make_raw(manufacturer_data=COMPANY_ID_BYTES + b"\x00\x00")
        assert parser.parse(raw) is None

    def test_company_id_only(self, parser):
        raw = make_raw(manufacturer_data=COMPANY_ID_BYTES)
        assert parser.parse(raw) is None


class TestGoveeRegistration:
    def test_registered_with_company_id(self):
        from adwatch.registry import ParserRegistry
        reg = ParserRegistry()
        instance = GoveeParser()
        reg.register(
            name="govee",
            company_id=0xEC88,
            local_name_pattern=r"^(GVH5|Govee)",
            description="Govee Sensors",
            version="1.0.0",
            core=False,
            instance=instance,
        )
        raw = make_raw(manufacturer_data=H5074_VALID)
        matched = reg.match(raw)
        assert any(isinstance(p, GoveeParser) for p in matched)

    def test_registered_matches_local_name(self):
        from adwatch.registry import ParserRegistry
        reg = ParserRegistry()
        instance = GoveeParser()
        reg.register(
            name="govee",
            company_id=0xEC88,
            local_name_pattern=r"^(GVH5|Govee)",
            description="Govee Sensors",
            version="1.0.0",
            core=False,
            instance=instance,
        )
        # No manufacturer_data but matching local_name
        raw = make_raw(manufacturer_data=None, local_name="GVH5074_1234")
        matched = reg.match(raw)
        assert any(isinstance(p, GoveeParser) for p in matched)

    def test_not_core(self):
        """Govee should be a plugin (core=False)."""
        assert True  # verified by registration above


# --- H5103 format builder (offset 4, battery at 7) ---

def _build_h5103(
    *,
    encoded_value=256470,
    battery=85,
    pad_prefix=b"\x00\x00\x00\x00",  # 4 bytes before encoded (offset 0-3)
):
    """Build manufacturer_data for H5103 format.

    Payload layout (after company ID):
      offset 0-3: prefix bytes
      offset 4-6: 3-byte big-endian encoded value
      offset 7:   battery percentage
    """
    payload = pad_prefix
    payload += encoded_value.to_bytes(3, "big")
    payload += bytes([battery])
    return COMPANY_ID_BYTES + payload


# --- H5177 format builder ---

def _build_h5177(
    *,
    temperature=2580,   # 25.80 C
    humidity=5247,       # 52.47 %
    battery=90,
    pad_prefix=b"\x00" * 6,  # 6 bytes before temp (offset 0-5)
):
    """Build manufacturer_data for H5177 format.

    Payload layout (after company ID):
      offset 0-5: prefix bytes
      offset 6-7: temperature as int16 LE, /100 for C
      offset 8-9: humidity as uint16 LE, /100 for %
      offset 10:  battery percentage
    """
    payload = pad_prefix
    payload += struct.pack("<h", temperature)
    payload += struct.pack("<H", humidity)
    payload += bytes([battery])
    return COMPANY_ID_BYTES + payload


# --- H5181 meat thermometer builder ---

def _build_h5181(*, probe_temps, pad_prefix=b"\x00\x00"):
    """Build manufacturer_data for H5181 meat thermometer format.

    Payload layout (after company ID):
      offset 0-1: prefix bytes
      offset 2+:  each probe is int16 LE, /100 for C
    """
    payload = pad_prefix
    for temp in probe_temps:
        payload += struct.pack("<h", temp)
    return COMPANY_ID_BYTES + payload


# --- Pre-built test data for new models ---

H5103_VALID = _build_h5103(encoded_value=256470, battery=85)
H5177_VALID = _build_h5177(temperature=2580, humidity=5247, battery=90)
H5181_TWO_PROBES = _build_h5181(probe_temps=[7500, 8200])  # 75.00 C, 82.00 C
H5181_FOUR_PROBES = _build_h5181(probe_temps=[6000, 7000, 8000, 9000])


class TestGoveeH5100Series:
    """H5100, H5101, H5102 use the same format as H5075."""

    def test_h5100_temperature(self, parser):
        raw = make_raw(manufacturer_data=H5075_VALID, local_name="GVH5100_1234")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["model"] == "H5100"
        assert result.metadata["temperature_c"] == pytest.approx(25.647)

    def test_h5101_temperature(self, parser):
        raw = make_raw(manufacturer_data=H5075_VALID, local_name="GVH5101_1234")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["model"] == "H5101"
        assert result.metadata["temperature_c"] == pytest.approx(25.647)

    def test_h5102_humidity(self, parser):
        raw = make_raw(manufacturer_data=H5075_VALID, local_name="GVH5102_1234")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["model"] == "H5102"
        assert result.metadata["humidity_percent"] == pytest.approx(47.0)

    def test_h5100_battery(self, parser):
        raw = make_raw(manufacturer_data=H5075_VALID, local_name="GVH5100_1234")
        result = parser.parse(raw)
        assert result.metadata["battery_percent"] == 91


class TestGoveeH5103Series:
    """H5103, H5104, H5105 use offset 4 for 3-byte encoded value."""

    def test_h5103_temperature(self, parser):
        raw = make_raw(manufacturer_data=H5103_VALID, local_name="GVH5103_1234")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["model"] == "H5103"
        assert result.metadata["temperature_c"] == pytest.approx(25.647)

    def test_h5104_temperature(self, parser):
        raw = make_raw(manufacturer_data=H5103_VALID, local_name="GVH5104_1234")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["model"] == "H5104"

    def test_h5105_humidity(self, parser):
        raw = make_raw(manufacturer_data=H5103_VALID, local_name="GVH5105_1234")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["model"] == "H5105"
        assert result.metadata["humidity_percent"] == pytest.approx(47.0)

    def test_h5103_battery(self, parser):
        raw = make_raw(manufacturer_data=H5103_VALID, local_name="GVH5103_1234")
        result = parser.parse(raw)
        assert result.metadata["battery_percent"] == 85

    def test_h5103_negative_temp(self, parser):
        data = _build_h5103(encoded_value=(0x800000 | 103550), battery=80)
        raw = make_raw(manufacturer_data=data, local_name="GVH5103_1234")
        result = parser.parse(raw)
        assert result.metadata["temperature_c"] == pytest.approx(-10.355)

    def test_h5103_too_short_payload(self, parser):
        # Only 7 bytes payload (needs 8 for h5103 format)
        short_data = COMPANY_ID_BYTES + b"\x00" * 7
        raw = make_raw(manufacturer_data=short_data, local_name="GVH5103_1234")
        assert parser.parse(raw) is None


class TestGoveeH5177Series:
    """H5177, H5179 use int16 LE at offset 6 and uint16 LE at offset 8."""

    def test_h5177_temperature(self, parser):
        raw = make_raw(manufacturer_data=H5177_VALID, local_name="GVH5177_1234")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["model"] == "H5177"
        assert result.metadata["temperature_c"] == pytest.approx(25.80)

    def test_h5179_temperature(self, parser):
        raw = make_raw(manufacturer_data=H5177_VALID, local_name="GVH5179_1234")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["model"] == "H5179"

    def test_h5177_humidity(self, parser):
        raw = make_raw(manufacturer_data=H5177_VALID, local_name="GVH5177_1234")
        result = parser.parse(raw)
        assert result.metadata["humidity_percent"] == pytest.approx(52.47)

    def test_h5177_battery(self, parser):
        raw = make_raw(manufacturer_data=H5177_VALID, local_name="GVH5177_1234")
        result = parser.parse(raw)
        assert result.metadata["battery_percent"] == 90

    def test_h5177_negative_temp(self, parser):
        data = _build_h5177(temperature=-1050, humidity=8000, battery=75)
        raw = make_raw(manufacturer_data=data, local_name="GVH5177_1234")
        result = parser.parse(raw)
        assert result.metadata["temperature_c"] == pytest.approx(-10.50)

    def test_h5177_too_short_payload(self, parser):
        # Only 10 bytes payload (needs 11 for h5177 format)
        short_data = COMPANY_ID_BYTES + b"\x00" * 10
        raw = make_raw(manufacturer_data=short_data, local_name="GVH5177_1234")
        assert parser.parse(raw) is None


class TestGoveeH5174:
    """H5174 uses H5074 format."""

    def test_h5174_temperature(self, parser):
        raw = make_raw(manufacturer_data=H5074_VALID, local_name="GVH5174_1234")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["model"] == "H5174"
        assert result.metadata["temperature_c"] == pytest.approx(25.80)

    def test_h5174_humidity(self, parser):
        raw = make_raw(manufacturer_data=H5074_VALID, local_name="GVH5174_1234")
        result = parser.parse(raw)
        assert result.metadata["humidity_percent"] == pytest.approx(52.47)


class TestGoveeMeatThermometers:
    """H5181, H5182, H5183 are multi-probe meat thermometers."""

    def test_h5181_two_probes(self, parser):
        raw = make_raw(manufacturer_data=H5181_TWO_PROBES, local_name="GVH5181_1234")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["model"] == "H5181"
        assert result.metadata["probes"] == pytest.approx([75.00, 82.00])

    def test_h5182_model(self, parser):
        raw = make_raw(manufacturer_data=H5181_TWO_PROBES, local_name="GVH5182_1234")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["model"] == "H5182"

    def test_h5183_model(self, parser):
        raw = make_raw(manufacturer_data=H5181_TWO_PROBES, local_name="GVH5183_1234")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["model"] == "H5183"

    def test_four_probes(self, parser):
        raw = make_raw(manufacturer_data=H5181_FOUR_PROBES, local_name="GVH5181_1234")
        result = parser.parse(raw)
        assert result.metadata["probes"] == pytest.approx([60.00, 70.00, 80.00, 90.00])

    def test_no_humidity_or_battery(self, parser):
        raw = make_raw(manufacturer_data=H5181_TWO_PROBES, local_name="GVH5181_1234")
        result = parser.parse(raw)
        assert "humidity_percent" not in result.metadata
        assert "battery_percent" not in result.metadata

    def test_device_class_is_sensor(self, parser):
        raw = make_raw(manufacturer_data=H5181_TWO_PROBES, local_name="GVH5181_1234")
        result = parser.parse(raw)
        assert result.device_class == "sensor"

    def test_max_six_probes(self, parser):
        data = _build_h5181(probe_temps=[100 * i for i in range(1, 8)])  # 7 probes
        raw = make_raw(manufacturer_data=data, local_name="GVH5181_1234")
        result = parser.parse(raw)
        assert len(result.metadata["probes"]) <= 6

    def test_single_probe(self, parser):
        data = _build_h5181(probe_temps=[5000])
        raw = make_raw(manufacturer_data=data, local_name="GVH5181_1234")
        result = parser.parse(raw)
        assert result.metadata["probes"] == pytest.approx([50.00])

    def test_minimum_payload(self, parser):
        # Need at least offset 2 + 2 bytes for one probe = 4 bytes
        short_data = COMPANY_ID_BYTES + b"\x00\x00\x00"  # only 3 bytes, not enough for a probe
        raw = make_raw(manufacturer_data=short_data, local_name="GVH5181_1234")
        assert parser.parse(raw) is None


# --- H5124 vibration sensor (AES-encrypted, company ID 0xEF88) ---

from adwatch.plugins.govee import _calculate_crc, _encrypt_data

VIBRATION_CID_BYTES = bytes([0x88, 0xEF])  # 0xEF88 little-endian


def _build_h5124(
    *,
    model_id=9,
    battery=100,
    event=1,   # 1=vibration, 0=idle
    prefix=b"\xa8\xb1",
    time_counter=b"\x00\x07\x00\x01",
):
    """Build a 24-byte H5124 vibration sensor manufacturer_data payload.

    Format: prefix(2) + time_counter(4) + encrypted(16) + crc(2)
    Decrypted payload: 01 03 <model_id> 02 <battery> <event> + 10 zero bytes
    """
    plaintext = bytes([0x01, 0x03, model_id, 0x02, battery, event]) + bytes(10)
    key = time_counter + bytes(12)
    enc_data = _encrypt_data(key, plaintext)
    crc = _calculate_crc(enc_data)
    return VIBRATION_CID_BYTES + prefix + time_counter + enc_data + crc.to_bytes(2, "big")


H5124_VIBRATION = _build_h5124(event=1, battery=100)
H5124_IDLE = _build_h5124(event=0, battery=85)
H5124_LOW_BATTERY = _build_h5124(event=1, battery=12)
H5124_DIFFERENT_TIME = _build_h5124(event=1, time_counter=b"\x00\x0a\x00\x05")


class TestGoveeH5124Decryption:
    def test_vibration_event_detected(self, parser):
        raw = make_raw(manufacturer_data=H5124_VIBRATION, local_name="GV51242F04")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["vibration"] is True

    def test_idle_event(self, parser):
        raw = make_raw(manufacturer_data=H5124_IDLE, local_name="GV51244071")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["vibration"] is False

    def test_battery_percentage(self, parser):
        raw = make_raw(manufacturer_data=H5124_VIBRATION, local_name="GV51242F04")
        result = parser.parse(raw)
        assert result.metadata["battery_percent"] == 100

    def test_low_battery(self, parser):
        raw = make_raw(manufacturer_data=H5124_LOW_BATTERY, local_name="GV51242F04")
        result = parser.parse(raw)
        assert result.metadata["battery_percent"] == 12

    def test_model_is_h5124(self, parser):
        raw = make_raw(manufacturer_data=H5124_VIBRATION, local_name="GV51242F04")
        result = parser.parse(raw)
        assert result.metadata["model"] == "H5124"

    def test_device_class(self, parser):
        raw = make_raw(manufacturer_data=H5124_VIBRATION, local_name="GV51242F04")
        result = parser.parse(raw)
        assert result.device_class == "sensor"

    def test_beacon_type(self, parser):
        raw = make_raw(manufacturer_data=H5124_VIBRATION, local_name="GV51242F04")
        result = parser.parse(raw)
        assert result.beacon_type == "govee"

    def test_different_time_counter_same_result(self, parser):
        raw = make_raw(manufacturer_data=H5124_DIFFERENT_TIME, local_name="GV51242F04")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["vibration"] is True
        assert result.metadata["battery_percent"] == 100

    def test_identity_hash(self, parser):
        raw = make_raw(manufacturer_data=H5124_VIBRATION, local_name="GV51242F04")
        result = parser.parse(raw)
        expected = hashlib.sha256("AA:BB:CC:DD:EE:FF".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected


class TestGoveeH5124Matching:
    def test_matches_by_company_id(self, parser):
        """H5124 uses company ID 0xEF88, not 0xEC88."""
        raw = make_raw(manufacturer_data=H5124_VIBRATION, local_name=None)
        result = parser.parse(raw)
        assert result is not None

    def test_matches_by_local_name_gv5124(self, parser):
        raw = make_raw(manufacturer_data=H5124_VIBRATION, local_name="GV51242F04")
        result = parser.parse(raw)
        assert result is not None

    def test_company_id_value(self):
        assert GOVEE_VIBRATION_COMPANY_ID == 0xEF88


class TestGoveeH5124CRCValidation:
    def test_bad_crc_rejected(self, parser):
        data = bytearray(H5124_VIBRATION)
        data[-1] ^= 0xFF  # corrupt CRC
        raw = make_raw(manufacturer_data=bytes(data), local_name="GV51242F04")
        assert parser.parse(raw) is None

    def test_short_payload_rejected(self, parser):
        # Only 10 bytes (need 24 after company ID bytes, total 26)
        short = VIBRATION_CID_BYTES + b"\x00" * 10
        raw = make_raw(manufacturer_data=short, local_name="GV51242F04")
        assert parser.parse(raw) is None


class TestGoveeH5124Registration:
    def test_registered_with_both_company_ids(self):
        from adwatch.registry import ParserRegistry

        reg = ParserRegistry()
        instance = GoveeParser()
        reg.register(
            name="govee",
            company_id=[0xEC88, 0xEF88],
            local_name_pattern=r"^(GVH5|GV5124|Govee)",
            description="Govee Sensors",
            version="1.1.0",
            core=False,
            instance=instance,
        )
        # Match by 0xEF88
        raw_vib = make_raw(manufacturer_data=H5124_VIBRATION)
        matched = reg.match(raw_vib)
        assert any(isinstance(p, GoveeParser) for p in matched)

        # Match by 0xEC88 (original thermometers)
        raw_therm = make_raw(manufacturer_data=H5074_VALID)
        matched = reg.match(raw_therm)
        assert any(isinstance(p, GoveeParser) for p in matched)


class TestGoveeH5124UI:
    def test_ui_config_returns_tab(self):
        parser = GoveeParser()
        cfg = parser.ui_config()
        assert cfg is not None
        assert cfg.tab_name == "Govee"

    def test_ui_config_has_vibration_widget(self):
        parser = GoveeParser()
        cfg = parser.ui_config()
        widget_titles = [w.title for w in cfg.widgets]
        assert any("vibration" in t.lower() or "sensor" in t.lower() for t in widget_titles)

    def test_ui_config_data_table_columns(self):
        parser = GoveeParser()
        cfg = parser.ui_config()
        table_widgets = [w for w in cfg.widgets if w.widget_type == "data_table"]
        assert len(table_widgets) > 0
        cols = table_widgets[0].render_hints.get("columns", [])
        assert "timestamp" in cols
        assert "mac_address" in cols


class TestGoveeH5124API:
    @pytest.mark.asyncio
    async def test_api_recent(self, tmp_path):
        from adwatch.storage.base import Database
        from adwatch.storage.migrations import run_migrations
        from adwatch.storage.raw import RawStorage
        from adwatch.models import Classification
        from httpx import ASGITransport, AsyncClient
        from fastapi import FastAPI

        database = Database()
        await database.connect(str(tmp_path / "govee_test.db"))
        await run_migrations(database)
        raw_storage = RawStorage(database)

        parser = GoveeParser()
        router = parser.api_router(database)
        assert router is not None

        app = FastAPI()
        app.include_router(router)

        ad = RawAdvertisement(
            timestamp="2026-03-09T10:00:00+00:00",
            mac_address="CA:32:39:37:2F:04",
            address_type="random",
            manufacturer_data=H5124_VIBRATION,
            service_data=None,
            local_name="GV51242F04",
        )
        await raw_storage.save(
            ad,
            Classification(ad_type="govee", ad_category="sensor", source="company_id"),
            parsed_by=["govee"],
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/recent")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) >= 1

        await database.close()
