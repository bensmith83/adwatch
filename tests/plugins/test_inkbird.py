"""Tests for Inkbird Sensors BLE parser plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.inkbird import InkbirdParser


@pytest.fixture
def parser():
    return InkbirdParser()


def make_raw(manufacturer_data=None, local_name=None, service_uuids=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-06T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        service_data=None,
        service_uuids=service_uuids or [],
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        manufacturer_data=manufacturer_data, local_name=local_name, **defaults
    )


# --- Helpers ---

FAKE_COMPANY_BYTES = bytes([0x09, 0x09])  # arbitrary company ID prefix
DISCONNECTED = -32768  # 0x8000 signed = probe disconnected
NO_PROBE = -10  # 0xFFF6 -- documented iBBQ "probe absent" sentinel

# iBBQ manufacturer_data carries a 10-byte header before the probe fields:
# sub-opcode(1) + header(2) + flag(1) + device MAC(6). See
# apk-ble-hunting/reports/{easybbq,bbqgo}_passive.md and plugins/ibbq.py.
IBBQ_HEADER = bytes([0x01, 0x00, 0x00, 0x00]) + b"\xff\xee\xdd\xcc\xbb\xaa"


def _build_ibbq(*probes_raw):
    """Build manufacturer_data for iBBQ: 10-byte header + 2 bytes per probe (LE signed)."""
    data = IBBQ_HEADER
    for val in probes_raw:
        data += struct.pack("<h", val)
    return data


def _build_ibs_th(temp_raw, humidity_raw, config=0, battery=87, flag=0):
    """Build the full 9-byte IBS-TH manufacturer_data (Encoding A).

    Per apk-ble-hunting inkbird-inkbirdapp_passive.md: IbsthPresenter feeds
    BluetoothDataParser.parseAdvData the scan-record hex from byte 14
    (substring(28)). For the "sps" advert (02 01 06 | 03 02 f0 ff |
    04 09 's' 'p' 's' | 0a ff <9 bytes>) byte 14 is the FIRST byte of the
    manufacturer data -- there is no SIG company ID, the "CID" bytes ARE the
    temperature. Layout: temp int16 LE /100 | hum int16 LE /100 | config u8 |
    2 reserved | battery u8 | data flag u8.
    """
    return (
        struct.pack("<h", temp_raw)
        + struct.pack("<h", humidity_raw)
        + bytes([config, 0x00, 0x00, battery, flag])
    )


# --- Pre-built test data ---

IBBQ_ONE_PROBE = _build_ibbq(250)       # 25.0°C
IBBQ_TWO_PROBES = _build_ibbq(250, 315)  # 25.0°C, 31.5°C
IBBQ_FOUR_PROBES = _build_ibbq(250, 315, 1000, 500)  # 25.0, 31.5, 100.0, 50.0
IBBQ_DISCONNECTED = _build_ibbq(250, DISCONNECTED)  # probe 1 ok, probe 2 disconnected
IBS_TH_DATA = _build_ibs_th(2350, 5500)  # 23.50°C, 55.00%


# --- iBBQ Probe Parsing ---

class TestIBBQProbes:
    def test_one_probe(self, parser):
        raw = make_raw(manufacturer_data=IBBQ_ONE_PROBE, local_name="iBBQ")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["probe_count"] == 1
        assert result.metadata["probe_1"] == 25.0

    def test_two_probes(self, parser):
        raw = make_raw(manufacturer_data=IBBQ_TWO_PROBES, local_name="iBBQ")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["probe_count"] == 2
        assert result.metadata["probe_1"] == 25.0
        assert result.metadata["probe_2"] == 31.5

    def test_four_probes(self, parser):
        raw = make_raw(manufacturer_data=IBBQ_FOUR_PROBES, local_name="iBBQ")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["probe_count"] == 4
        assert result.metadata["probe_1"] == 25.0
        assert result.metadata["probe_2"] == 31.5
        assert result.metadata["probe_3"] == 100.0
        assert result.metadata["probe_4"] == 50.0

    def test_disconnected_probe(self, parser):
        raw = make_raw(manufacturer_data=IBBQ_DISCONNECTED, local_name="iBBQ")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["probe_count"] == 2
        assert result.metadata["probe_1"] == 25.0
        assert result.metadata["probe_2"] is None  # disconnected

    def test_device_type_ibbq(self, parser):
        raw = make_raw(manufacturer_data=IBBQ_ONE_PROBE, local_name="iBBQ")
        result = parser.parse(raw)
        assert result.metadata["device_type"] == "ibbq"

    def test_negative_temperature(self, parser):
        data = _build_ibbq(-50)  # -5.0°C
        raw = make_raw(manufacturer_data=data, local_name="iBBQ")
        result = parser.parse(raw)
        assert result.metadata["probe_1"] == -5.0

    def test_no_probe_sentinel(self, parser):
        """0xFFF6 (-10 raw) is the documented iBBQ probe-absent sentinel."""
        data = _build_ibbq(250, NO_PROBE)
        raw = make_raw(manufacturer_data=data, local_name="iBBQ")
        result = parser.parse(raw)
        assert result.metadata["probe_count"] == 2
        assert result.metadata["probe_1"] == 25.0
        assert result.metadata["probe_2"] is None


# --- IBS-TH Parsing ---

class TestIBSTH:
    def test_temp_and_humidity(self, parser):
        raw = make_raw(manufacturer_data=IBS_TH_DATA, local_name="sps")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["temperature"] == 23.5
        assert result.metadata["humidity"] == 55.0

    def test_device_type_ibs_th(self, parser):
        raw = make_raw(manufacturer_data=IBS_TH_DATA, local_name="sps")
        result = parser.parse(raw)
        assert result.metadata["device_type"] == "ibs_th"

    def test_sps_prefix_match(self, parser):
        raw = make_raw(manufacturer_data=IBS_TH_DATA, local_name="sps 12345")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["device_type"] == "ibs_th"

    def test_negative_temp(self, parser):
        data = _build_ibs_th(-500, 6000)  # -5.00°C, 60.00%
        raw = make_raw(manufacturer_data=data, local_name="sps")
        result = parser.parse(raw)
        assert result.metadata["temperature"] == -5.0
        assert result.metadata["humidity"] == 60.0


# --- ParseResult Fields ---

class TestInkbirdFrameFields:
    def test_parser_name(self, parser):
        raw = make_raw(manufacturer_data=IBBQ_ONE_PROBE, local_name="iBBQ")
        result = parser.parse(raw)
        assert result.parser_name == "inkbird"

    def test_beacon_type(self, parser):
        raw = make_raw(manufacturer_data=IBBQ_ONE_PROBE, local_name="iBBQ")
        result = parser.parse(raw)
        assert result.beacon_type == "inkbird"

    def test_device_class(self, parser):
        raw = make_raw(manufacturer_data=IBBQ_ONE_PROBE, local_name="iBBQ")
        result = parser.parse(raw)
        assert result.device_class == "sensor"

    def test_raw_payload_hex(self, parser):
        raw = make_raw(manufacturer_data=IBBQ_ONE_PROBE, local_name="iBBQ")
        result = parser.parse(raw)
        expected = IBBQ_ONE_PROBE[10:].hex()
        assert result.raw_payload_hex == expected

    def test_ibs_th_raw_payload_hex(self, parser):
        raw = make_raw(manufacturer_data=IBS_TH_DATA, local_name="sps")
        result = parser.parse(raw)
        expected = IBS_TH_DATA.hex()
        assert result.raw_payload_hex == expected


class TestIBSTHEncodingA:
    def test_hand_built_scan_record_offset_basis(self, parser):
        """Pin the byte-14 scan-record basis to manufacturer_data[0]."""
        mfr = _build_ibs_th(2134, 4567, battery=64)
        record = (
            bytes.fromhex("020106") + bytes.fromhex("0302f0ff")
            + bytes([0x04, 0x09]) + b"sps" + bytes([len(mfr) + 1, 0xFF]) + mfr
        )
        str3 = record.hex()[28:]
        assert bytes.fromhex(str3) == mfr
        result = parser.parse(make_raw(manufacturer_data=mfr, local_name="sps"))
        assert result.metadata["temperature"] == pytest.approx(21.34)
        assert result.metadata["humidity"] == pytest.approx(45.67)
        assert result.metadata["battery"] == 64

    def test_sensor_config_external_probe(self, parser):
        data = _build_ibs_th(-1250, 3000, config=1)
        result = parser.parse(make_raw(manufacturer_data=data, local_name="sps"))
        assert result.metadata["temperature"] == pytest.approx(-12.5)
        assert result.metadata["sensor_config"] == "external_temp_internal_hum"

    def test_must_read_flag(self, parser):
        data = _build_ibs_th(2000, 5000, flag=6)
        result = parser.parse(make_raw(manufacturer_data=data, local_name="sps"))
        assert result.metadata["must_read"] is True

    def test_tps_temperature_only(self, parser):
        data = _build_ibs_th(1800, 9999)
        result = parser.parse(make_raw(manufacturer_data=data, local_name="tps"))
        assert result is not None
        assert result.metadata["device_type"] == "ibs_th"
        assert result.metadata["temperature"] == pytest.approx(18.0)
        assert "humidity" not in result.metadata
        assert result.storage_row["humidity"] is None


class TestInkbirdNamedModels:
    @pytest.mark.parametrize("name", [
        "ITH-21-B", "ITH-11-B", "IBS-P02B", "IBS-Mini", "INT-11P-B", "IDT-34c-B",
        "IBT-4WB", "ISC-029-BW", "BG-BT1W", "ITC-312", "Ink@IAM-T1",
        "Inkbird@IBT-24SPH", "INKBIRD@IBT-4XB", "IHT-2PB", "COBB-11P-B",
    ])
    def test_model_name_presence(self, parser, name):
        result = parser.parse(make_raw(manufacturer_data=b"\x01\x02\x03\x04", local_name=name))
        assert result is not None
        assert result.metadata["device_type"] == "inkbird_named"
        assert result.metadata["model"] == name
        assert result.storage_table is None

    def test_named_model_without_mfr_data(self, parser):
        result = parser.parse(make_raw(local_name="ITH-13-B"))
        assert result is not None

    def test_registry_name_pattern_covers_models(self):
        from adwatch.plugins.inkbird import INKBIRD_NAME_PATTERN
        import re
        for n in ("sps", "tps", "iBBQ", "ITH-21-B", "Ink@IAM-T2", "ITC-312"):
            assert re.match(INKBIRD_NAME_PATTERN, n)
        for n in ("xBBQ", "GrillEye", "tpsx-other", "Thermo"):
            assert not re.match(INKBIRD_NAME_PATTERN, n)


# --- Identity ---

class TestInkbirdIdentity:
    def test_identity_hash_from_mac(self, parser):
        raw = make_raw(manufacturer_data=IBBQ_ONE_PROBE, local_name="iBBQ")
        result = parser.parse(raw)
        expected = hashlib.sha256("AA:BB:CC:DD:EE:FF".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_length(self, parser):
        raw = make_raw(manufacturer_data=IBBQ_ONE_PROBE, local_name="iBBQ")
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)  # must be valid hex


# --- Rejection ---

class TestInkbirdRejectsInvalid:
    def test_no_local_name(self, parser):
        raw = make_raw(manufacturer_data=IBBQ_ONE_PROBE, local_name=None)
        assert parser.parse(raw) is None

    def test_wrong_local_name(self, parser):
        raw = make_raw(manufacturer_data=IBBQ_ONE_PROBE, local_name="Oral-B Toothbrush")
        assert parser.parse(raw) is None

    def test_no_manufacturer_data(self, parser):
        raw = make_raw(manufacturer_data=None, local_name="iBBQ")
        assert parser.parse(raw) is None

    def test_empty_manufacturer_data(self, parser):
        raw = make_raw(manufacturer_data=b"", local_name="iBBQ")
        assert parser.parse(raw) is None

    def test_too_short_ibbq(self, parser):
        # Need at least the 10-byte header + 1 probe (2) = 12 bytes
        raw = make_raw(manufacturer_data=FAKE_COMPANY_BYTES + b"\x01", local_name="iBBQ")
        assert parser.parse(raw) is None

    def test_header_only_ibbq(self, parser):
        # 10-byte header with no probe fields is not a reading
        raw = make_raw(manufacturer_data=IBBQ_HEADER, local_name="iBBQ")
        assert parser.parse(raw) is None

    def test_too_short_ibs_th(self, parser):
        # Need at least temp (2) + humidity (2) = 4 bytes of manufacturer_data
        raw = make_raw(manufacturer_data=b"\x01\x02\x03", local_name="sps")
        assert parser.parse(raw) is None


# --- Registration ---

class TestInkbirdRegistration:
    def test_registered_matches_local_name_ibbq(self):
        from adwatch.registry import ParserRegistry
        reg = ParserRegistry()
        instance = InkbirdParser()
        reg.register(
            name="inkbird",
            service_uuid="0000fff0-0000-1000-8000-00805f9b34fb",
            local_name_pattern=r"^(iBBQ|sps)",
            description="Inkbird Sensors",
            version="1.0.0",
            core=False,
            instance=instance,
        )
        raw = make_raw(manufacturer_data=IBBQ_ONE_PROBE, local_name="iBBQ")
        matched = reg.match(raw)
        assert any(isinstance(p, InkbirdParser) for p in matched)

    def test_registered_matches_local_name_sps(self):
        from adwatch.registry import ParserRegistry
        reg = ParserRegistry()
        instance = InkbirdParser()
        reg.register(
            name="inkbird",
            service_uuid="0000fff0-0000-1000-8000-00805f9b34fb",
            local_name_pattern=r"^(iBBQ|sps)",
            description="Inkbird Sensors",
            version="1.0.0",
            core=False,
            instance=instance,
        )
        raw = make_raw(manufacturer_data=IBS_TH_DATA, local_name="sps")
        matched = reg.match(raw)
        assert any(isinstance(p, InkbirdParser) for p in matched)

    def test_registered_matches_service_uuid(self):
        from adwatch.registry import ParserRegistry
        reg = ParserRegistry()
        instance = InkbirdParser()
        reg.register(
            name="inkbird",
            service_uuid="0000fff0-0000-1000-8000-00805f9b34fb",
            local_name_pattern=r"^(iBBQ|sps)",
            description="Inkbird Sensors",
            version="1.0.0",
            core=False,
            instance=instance,
        )
        raw = make_raw(
            manufacturer_data=IBBQ_ONE_PROBE,
            local_name="iBBQ",
            service_uuids=["0000fff0-0000-1000-8000-00805f9b34fb"],
        )
        matched = reg.match(raw)
        assert any(isinstance(p, InkbirdParser) for p in matched)


# --- UI Tab ---

class TestInkbirdUIConfig:
    def test_ui_config_returns_tab(self, parser):
        cfg = parser.ui_config()
        assert cfg is not None
        assert cfg.tab_name == "Inkbird"

    def test_ui_config_has_sensor_card(self, parser):
        cfg = parser.ui_config()
        widget_types = [w.widget_type for w in cfg.widgets]
        assert "sensor_card" in widget_types

    def test_ui_config_has_render_hints(self, parser):
        cfg = parser.ui_config()
        sensor_widgets = [w for w in cfg.widgets if w.widget_type == "sensor_card"]
        assert len(sensor_widgets) > 0
        assert "primary_field" in sensor_widgets[0].render_hints


# --- Storage Schema ---

class TestInkbirdStorageSchema:
    def test_storage_schema_creates_table(self, parser):
        schema = parser.storage_schema()
        assert schema is not None
        assert "inkbird_readings" in schema


# --- Parse Result Storage Fields ---

class TestInkbirdParseStorage:
    def test_parse_ibbq_includes_storage(self, parser):
        raw = make_raw(manufacturer_data=IBBQ_ONE_PROBE, local_name="iBBQ")
        result = parser.parse(raw)
        assert result.event_type == "inkbird_reading"
        assert result.storage_table == "inkbird_readings"
        assert result.storage_row is not None
        assert "temperature" in result.storage_row or "probe_1" in result.storage_row

    def test_parse_ibs_th_includes_storage(self, parser):
        raw = make_raw(manufacturer_data=IBS_TH_DATA, local_name="sps")
        result = parser.parse(raw)
        assert result.event_type == "inkbird_reading"
        assert result.storage_table == "inkbird_readings"
        assert result.storage_row is not None
        assert "temperature" in result.storage_row


# --- API Router ---

class TestInkbirdAPIRouter:
    def test_api_router_returns_router(self, parser):
        from unittest.mock import MagicMock
        db = MagicMock()
        router = parser.api_router(db)
        assert router is not None
