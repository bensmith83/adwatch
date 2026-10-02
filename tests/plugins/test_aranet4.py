"""Tests for Aranet4 CO2 monitor plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.aranet4 import Aranet4Parser


ARANET_UUID = "f0cd3001-95da-4f4b-9ac8-aa55d312af0c"


@pytest.fixture
def parser():
    return Aranet4Parser()


def make_raw(service_data=None, local_name=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-06T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="public",
        manufacturer_data=None,
        service_uuids=[ARANET_UUID],
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        service_data=service_data,
        local_name=local_name,
        **defaults,
    )


def build_aranet4(co2=450, temp_raw=440, pressure_raw=10130, humidity=55,
                   battery=85, status=1, interval=60, age=15):
    """Build 13-byte Aranet4 payload.

    Default: CO2=450ppm, temp=22.0C (440/20), pressure=1013.0hPa (10130/10),
    humidity=55%, battery=85%, green status, 60s interval, 15s age.
    """
    data = struct.pack("<H", co2)
    data += struct.pack("<H", temp_raw)
    data += struct.pack("<H", pressure_raw)
    data += bytes([humidity, battery, status])
    data += struct.pack("<H", interval)
    data += struct.pack("<H", age)
    return data


NORMAL_DATA = build_aranet4()


class TestAranet4Parsing:
    def test_parse_valid(self, parser):
        raw = make_raw(
            service_data={ARANET_UUID: NORMAL_DATA},
            local_name="Aranet4 12345",
        )
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(service_data={ARANET_UUID: NORMAL_DATA}, local_name="Aranet4 12345")
        result = parser.parse(raw)
        assert result.parser_name == "aranet4"

    def test_beacon_type(self, parser):
        raw = make_raw(service_data={ARANET_UUID: NORMAL_DATA}, local_name="Aranet4 12345")
        result = parser.parse(raw)
        assert result.beacon_type == "aranet4"

    def test_device_class(self, parser):
        raw = make_raw(service_data={ARANET_UUID: NORMAL_DATA}, local_name="Aranet4 12345")
        result = parser.parse(raw)
        assert result.device_class == "sensor"

    def test_co2(self, parser):
        raw = make_raw(service_data={ARANET_UUID: NORMAL_DATA}, local_name="Aranet4 12345")
        result = parser.parse(raw)
        assert result.metadata["co2_ppm"] == 450

    def test_temperature(self, parser):
        """temp_raw=440 / 20 = 22.0C."""
        raw = make_raw(service_data={ARANET_UUID: NORMAL_DATA}, local_name="Aranet4 12345")
        result = parser.parse(raw)
        assert result.metadata["temperature_c"] == pytest.approx(22.0)

    def test_pressure(self, parser):
        """pressure_raw=10130 / 10 = 1013.0 hPa."""
        raw = make_raw(service_data={ARANET_UUID: NORMAL_DATA}, local_name="Aranet4 12345")
        result = parser.parse(raw)
        assert result.metadata["pressure_hpa"] == pytest.approx(1013.0)

    def test_humidity(self, parser):
        raw = make_raw(service_data={ARANET_UUID: NORMAL_DATA}, local_name="Aranet4 12345")
        result = parser.parse(raw)
        assert result.metadata["humidity"] == 55

    def test_battery(self, parser):
        raw = make_raw(service_data={ARANET_UUID: NORMAL_DATA}, local_name="Aranet4 12345")
        result = parser.parse(raw)
        assert result.metadata["battery"] == 85


class TestAranet4Status:
    # parseColor (readingParsing_es5.js:95-100): value&3 -> 0=error,
    # 1=green, 2=yellow, 3=red. The original plugin used 0/1/2 = green/yellow/red.
    def test_status_error(self, parser):
        data = build_aranet4(status=0)
        raw = make_raw(service_data={ARANET_UUID: data}, local_name="Aranet4 12345")
        assert parser.parse(raw).metadata["status"] == "error"

    def test_status_ignores_upper_bits(self, parser):
        data = build_aranet4(status=0xF2)
        raw = make_raw(service_data={ARANET_UUID: data}, local_name="Aranet4 12345")
        assert parser.parse(raw).metadata["status"] == "yellow"

    def test_status_green(self, parser):
        data = build_aranet4(status=1)
        raw = make_raw(service_data={ARANET_UUID: data}, local_name="Aranet4 12345")
        result = parser.parse(raw)
        assert result.metadata["status"] == "green"

    def test_status_yellow(self, parser):
        data = build_aranet4(status=2)
        raw = make_raw(service_data={ARANET_UUID: data}, local_name="Aranet4 12345")
        result = parser.parse(raw)
        assert result.metadata["status"] == "yellow"

    def test_status_red(self, parser):
        data = build_aranet4(status=3)
        raw = make_raw(service_data={ARANET_UUID: data}, local_name="Aranet4 12345")
        result = parser.parse(raw)
        assert result.metadata["status"] == "red"

    def test_interval(self, parser):
        raw = make_raw(service_data={ARANET_UUID: NORMAL_DATA}, local_name="Aranet4 12345")
        result = parser.parse(raw)
        assert result.metadata["interval_s"] == 60

    def test_age(self, parser):
        raw = make_raw(service_data={ARANET_UUID: NORMAL_DATA}, local_name="Aranet4 12345")
        result = parser.parse(raw)
        assert result.metadata["age_s"] == 15


class TestAranet4Identity:
    def test_identity_hash_format(self, parser):
        raw = make_raw(service_data={ARANET_UUID: NORMAL_DATA}, local_name="Aranet4 12345")
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_identity_hash_uses_mac_and_name(self, parser):
        raw = make_raw(
            service_data={ARANET_UUID: NORMAL_DATA},
            local_name="Aranet4 12345",
            mac_address="11:22:33:44:55:66",
        )
        result = parser.parse(raw)
        # Name suffix is a stable per-device serial fragment (report) -> name basis
        expected = hashlib.sha256("aranet:Aranet4 12345".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected


class TestAranet4Malformed:
    # With no readable reading block the device is still identified
    # (presence + model) -- report "Fallback" section.
    def test_presence_no_service_data(self, parser):
        result = parser.parse(make_raw(service_data=None, local_name="Aranet4 12345"))
        assert result is not None
        assert result.metadata["model"] == "Aranet4"
        assert "co2_ppm" not in result.metadata

    def test_presence_wrong_uuid(self, parser):
        result = parser.parse(make_raw(service_data={"abcd": NORMAL_DATA}, local_name="Aranet4 12345"))
        assert "co2_ppm" not in result.metadata

    def test_presence_too_short(self, parser):
        result = parser.parse(make_raw(service_data={ARANET_UUID: bytes(5)}, local_name="Aranet4 12345"))
        assert "co2_ppm" not in result.metadata

    def test_returns_none_unrelated(self, parser):
        raw = make_raw(service_data=None, local_name="Thermo", service_uuids=[])
        assert parser.parse(raw) is None


class TestAranetEnrichment:
    def test_negative_temperature_signed(self, parser):
        data = build_aranet4(temp_raw=-100 & 0xFFFF)
        raw = make_raw(service_data={ARANET_UUID: data}, local_name="Aranet4 12345")
        assert parser.parse(raw).metadata["temperature_c"] == pytest.approx(-5.0)

    def test_fce0_service_uuid_presence(self, parser):
        raw = make_raw(service_data=None, local_name=None,
                       service_uuids=["0000fce0-0000-1000-8000-00805f9b34fb"])
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["model"] == "Aranet"
        h = hashlib.sha256("AA:BB:CC:DD:EE:FF".encode()).hexdigest()[:16]
        assert result.identifier_hash == h

    def test_saf_company_id_presence(self, parser):
        raw = make_raw(service_data=None, local_name=None, service_uuids=[],
                       manufacturer_data=bytes([0x02, 0x07, 0x21, 0x00]))
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["model"] == "Aranet"

    @pytest.mark.parametrize("name,model", [
        ("Aranet2 1A2B3", "Aranet2"),
        ("Aranet Radon 0F11", "Aranet Radon"),
        ("Aranet\u2622 123", "Aranet Nucleo"),
        ("Aranet4 12345", "Aranet4"),
    ])
    def test_model_from_name(self, parser, name, model):
        result = parser.parse(make_raw(service_data=None, local_name=name, service_uuids=[]))
        assert result.metadata["model"] == model

    def test_registration_covers_fce0_cid_and_names(self):
        from adwatch.registry import ParserRegistry
        from adwatch.plugins import aranet4 as mod
        reg = ParserRegistry()
        reg.register(
            name="aranet4", company_id=mod.SAF_COMPANY_ID,
            service_uuid=mod.ARANET_SERVICE_UUIDS,
            local_name_pattern=mod.ARANET_NAME_PATTERN,
            description="t", version="t", core=False, instance=Aranet4Parser(),
        )
        assert mod.SAF_COMPANY_ID == 0x0702
        for raw in (
            make_raw(service_uuids=["fce0"]),
            make_raw(service_uuids=[ARANET_UUID]),
            make_raw(service_uuids=[], manufacturer_data=bytes([0x02, 0x07, 0x00])),
            make_raw(service_uuids=[], local_name="Aranet2 ABCDE"),
        ):
            assert len(reg.match(raw)) == 1
