"""Tests for SensorPush plugin.

Layout per apk-ble-hunting report cousins-sears-beaconthermometer_passive.md
(CSSensorService$2.onScanResult). The app copies the AD 0xFF *value* (all
bytes after the AD type, i.e. the full manufacturer_data INCLUDING the two
bytes adwatch treats as a CID). So report offset mfg[N] == manufacturer_data[N]
== manufacturer_payload[N-2]. SensorPush has no real SIG CID.

Packed samples (V2) use mixed-radix packing per res/raw/definitions.json
packParams [min, max, resolution]: steps = 1 + (max-min)/res; field k =
(packed // prod(prev steps)) % steps_k.
"""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.sensorpush import SensorPushParser


@pytest.fixture
def parser():
    return SensorPushParser()


def make_raw(manufacturer_data=None, local_name="SensorPush HT.w 1234", **kwargs):
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


def pack(fields, params):
    value = 0
    mult = 1
    for v, (lo, hi, res) in zip(fields, params):
        steps = int(round(1 + (hi - lo) / res))
        value += int(round((v - lo) / res)) * mult
        mult *= steps
    return value


HTW = [(-40.0, 125.0, 0.0025), (0.0, 100.0, 0.0025)]
HTPXW = [(-40.0, 140.0, 0.0025), (0.0, 100.0, 0.0025), (30000.0, 125000.0, 1.0)]
TC = [(-200.0, 1800.0, 0.0625)]


def v2_data(version, fields, params, nbytes, ptype=0):
    header = ((version - 64) << 2) | ptype
    return bytes([header]) + pack(fields, params).to_bytes(nbytes, "little")


HTW_DATA = v2_data(65, [22.5, 45.0], HTW, 4)


class TestFullAdvertOffsetBasis:
    def test_hand_built_scan_record_offsets(self, parser):
        """Full AD 0xFF from a scan record: 06 FF <hdr> <4B packed>.

        The app's bArr starts right after the 0xFF type byte, so header is
        manufacturer_data[0], not manufacturer_payload[0].
        """
        scan_record = bytes([0x06, 0xFF]) + HTW_DATA
        ad_len = scan_record[0]
        mfr = scan_record[2:1 + ad_len]
        assert mfr == HTW_DATA
        result = parser.parse(make_raw(manufacturer_data=mfr))
        assert result is not None
        assert result.metadata["model"] == "HT.w"
        assert result.metadata["device_version"] == 65
        assert result.metadata["temperature_c"] == pytest.approx(22.5)
        assert result.metadata["humidity"] == pytest.approx(45.0)


class TestSensorPushBasics:
    def test_parse_valid(self, parser):
        result = parser.parse(make_raw(manufacturer_data=HTW_DATA))
        assert isinstance(result, ParseResult)
        assert result.parser_name == "sensorpush"
        assert result.beacon_type == "sensorpush"
        assert result.device_class == "sensor"
        assert result.metadata["packet_type"] == "data"

    def test_htw_negative_temp(self, parser):
        data = v2_data(65, [-12.25, 80.5], HTW, 4)
        result = parser.parse(make_raw(manufacturer_data=data))
        assert result.metadata["temperature_c"] == pytest.approx(-12.25)
        assert result.metadata["humidity"] == pytest.approx(80.5)

    def test_htw_temp_above_16bit_range(self, parser):
        """HT.w temp has 66001 steps — only fits mixed-radix, not 16-bit fields."""
        data = v2_data(65, [120.0, 10.0], HTW, 4)
        result = parser.parse(make_raw(manufacturer_data=data))
        assert result.metadata["temperature_c"] == pytest.approx(120.0)
        assert result.metadata["humidity"] == pytest.approx(10.0)

    def test_htp_xw_pressure(self, parser):
        data = v2_data(64, [21.0, 50.0, 101325.0], HTPXW, 6)
        assert len(data) == 7
        result = parser.parse(make_raw(manufacturer_data=data, local_name="SensorPush HTP.xw AB12"))
        assert result.metadata["model"] == "HTP.xw"
        assert result.metadata["temperature_c"] == pytest.approx(21.0)
        assert result.metadata["humidity"] == pytest.approx(50.0)
        assert result.metadata["pressure_pa"] == pytest.approx(101325.0)
        assert result.metadata["pressure_hpa"] == pytest.approx(1013.25)

    def test_tc_probe(self, parser):
        data = v2_data(66, [100.0], TC, 2)
        result = parser.parse(make_raw(manufacturer_data=data, local_name="SensorPush TC"))
        assert result.metadata["model"] == "TC"
        assert result.metadata["probe_temperature_c"] == pytest.approx(100.0)
        assert "humidity" not in result.metadata

    def test_v2_id_packet(self, parser):
        dev_id = 0x12345678
        data = bytes([((65 - 64) << 2) | 3]) + (dev_id | 0x80000000).to_bytes(4, "little")
        result = parser.parse(make_raw(manufacturer_data=data))
        assert result.metadata["packet_type"] == "device_id"
        assert result.metadata["device_id"] == dev_id
        assert result.metadata["initialized"] is False
        assert "temperature_c" not in result.metadata
        expected = hashlib.sha256(f"sensorpush:{dev_id}".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_v2_id_packet_initialized(self, parser):
        data = bytes([0x07]) + (0x00ABCDEF).to_bytes(4, "little")
        result = parser.parse(make_raw(manufacturer_data=data))
        assert result.metadata["initialized"] is True
        assert result.metadata["device_id"] == 0x00ABCDEF

    def test_ht1_full_packet(self, parser):
        # bytes 0-3 packed sample; byte3 bits 2-6 = version 1; bit7 = not-init
        data = bytes([0x11, 0x22, 0x33, 0x04 | 0x01]) + (0x0A0B0C).to_bytes(3, "little")
        result = parser.parse(make_raw(manufacturer_data=data, local_name="SensorPush HT 5678"))
        assert result.metadata["model"] == "HT1"
        assert result.metadata["device_version"] == 1
        assert result.metadata["device_id"] == 0x0A0B0C
        assert result.metadata["initialized"] is True
        assert result.metadata["packed_sample_hex"] == "11223305"
        expected = hashlib.sha256(f"sensorpush:{0x0A0B0C}".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_ht1_short_packet_not_initialized(self, parser):
        data = bytes([0x11, 0x22, 0x33, 0x80 | 0x04])
        result = parser.parse(make_raw(manufacturer_data=data, local_name="SensorPush HT 5678"))
        assert result.metadata["model"] == "HT1"
        assert result.metadata["initialized"] is False
        assert "device_id" not in result.metadata


class TestSensorPushMatching:
    def test_rejects_without_name(self, parser):
        assert parser.parse(make_raw(manufacturer_data=HTW_DATA, local_name=None)) is None

    def test_rejects_wrong_name(self, parser):
        assert parser.parse(make_raw(manufacturer_data=HTW_DATA, local_name="OtherDevice")) is None

    def test_name_only_presence(self, parser):
        """Name match with no mfr data -> presence-only result (uninitialized HT1 case)."""
        result = parser.parse(make_raw(manufacturer_data=None))
        assert result is not None
        assert "temperature_c" not in result.metadata

    def test_unknown_layout_still_named(self, parser):
        result = parser.parse(make_raw(manufacturer_data=b"\xff\xff"))
        assert result is not None
        assert "temperature_c" not in result.metadata


class TestSensorPushIdentity:
    def test_data_packet_identity_falls_back_to_mac_and_name(self, parser):
        raw = make_raw(manufacturer_data=HTW_DATA, mac_address="11:22:33:44:55:66")
        result = parser.parse(raw)
        expected = hashlib.sha256(
            "11:22:33:44:55:66:SensorPush HT.w 1234".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected
