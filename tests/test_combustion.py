"""Tests for Combustion Inc predictive thermometer plugin.

Byte layouts per apk-ble-hunting/reports/combustion-app_passive.md.
"""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.combustion import (
    CombustionParser,
    COMBUSTION_COMPANY_ID,
    COMBUSTION_SERVICE_UUID,
    PRODUCT_TYPES,
    PROBE_MODES,
    PROBE_COLORS,
    DFU_NAME_PREFIXES,
    decode_temperatures_13bit,
)


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


def _mfr(payload: bytes) -> bytes:
    return struct.pack("<H", COMBUSTION_COMPANY_ID) + payload


def _register(registry):
    @register_parser(
        name="combustion",
        company_id=COMBUSTION_COMPANY_ID,
        service_uuid=COMBUSTION_SERVICE_UUID,
        local_name_pattern=r"^(Thermom_DFU_|Display_DFU_|Charger_DFU_|Gauge_DFU_|CI Probe BL|CI Timer BL|CI Gauge BL)",
        description="Combustion",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(CombustionParser):
        pass

    return _P


class TestCombustionConstants:
    def test_company_id(self):
        assert COMBUSTION_COMPANY_ID == 0x09C7

    def test_service_uuid(self):
        assert COMBUSTION_SERVICE_UUID == "00000100-caab-3792-3d44-97ae51c1407a"

    def test_product_types_known(self):
        assert PRODUCT_TYPES[0x01] == "PROBE"
        assert PRODUCT_TYPES[0x02] == "NODE"
        assert PRODUCT_TYPES[0x03] == "GAUGE"

    def test_dfu_prefixes(self):
        assert "Thermom_DFU_" in DFU_NAME_PREFIXES


class TestCombustionMatching:
    def test_match_service_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[COMBUSTION_SERVICE_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_company_id(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=_mfr(b"\x01" + bytes(20)))
        assert len(registry.match(ad)) == 1

    def test_match_dfu_name_prefix(self):
        registry = ParserRegistry()
        _register(registry)
        for name in (
            "Thermom_DFU_ABCD",
            "Display_DFU_99",
            "Charger_DFU_X",
            "Gauge_DFU_1",
            "CI Probe BL",
            "CI Timer BL",
            "CI Gauge BL",
        ):
            ad = _make_ad(local_name=name)
            assert len(registry.match(ad)) == 1, name


class TestTemperatureDecode:
    def test_decode_zero_returns_eight_minimum_temps(self):
        # All-zero raw 13-bit values: T = 0 * 0.05 - 20 = -20 °C
        temps = decode_temperatures_13bit(bytes(13))
        assert len(temps) == 8
        assert all(t == pytest.approx(-20.0) for t in temps)

    def test_decode_known_pattern(self):
        # raw value 1000 in all 8 slots → T = 1000 * 0.05 - 20 = 30 °C
        # Encode 8x 13-bit value=1000 packed LE into 13 bytes.
        raw = 1000
        bits = 0
        for i in range(8):
            bits |= raw << (i * 13)
        packed = bits.to_bytes(13, "little")
        temps = decode_temperatures_13bit(packed)
        assert all(t == pytest.approx(30.0) for t in temps)

    def test_decode_mixed_values(self):
        # Different value per slot.
        values = [400, 600, 800, 1000, 1200, 1400, 1600, 1800]
        bits = 0
        for i, v in enumerate(values):
            bits |= v << (i * 13)
        packed = bits.to_bytes(13, "little")
        temps = decode_temperatures_13bit(packed)
        for got, raw in zip(temps, values):
            assert got == pytest.approx(raw * 0.05 - 20.0)


class TestProbeParsing:
    def _parse(self, **kwargs):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(**kwargs)
        matched = registry.match(ad)
        assert matched
        return matched[0].parse(ad)

    def test_probe_full_payload_decodes_all_fields(self):
        # product=0x01 (PROBE), serial=0x12345678, all temps=raw 1000 (=30C),
        # mode/color/id=0x00, status=0x00, hop_count=0
        serial = struct.pack("<I", 0x12345678)
        raw = 1000
        bits = 0
        for i in range(8):
            bits |= raw << (i * 13)
        temp_bytes = bits.to_bytes(13, "little")
        payload = b"\x01" + serial + temp_bytes + b"\x00\x00\x00"
        assert len(payload) == 21

        result = self._parse(
            manufacturer_data=_mfr(payload),
            service_uuids=[COMBUSTION_SERVICE_UUID],
        )
        assert result.metadata["product_type"] == "PROBE"
        assert result.metadata["serial_number"] == 0x12345678
        assert all(t == pytest.approx(30.0) for t in result.metadata["temperatures_c"])
        assert result.metadata["hop_count"] == 0

    def test_probe_status_battery_low_bit(self):
        # bit 0 = 1 means battery LOW per report
        payload = b"\x01" + bytes(4) + bytes(13) + b"\x00\x01\x00"
        result = self._parse(
            manufacturer_data=_mfr(payload),
            service_uuids=[COMBUSTION_SERVICE_UUID],
        )
        assert result.metadata["battery_low"] is True

    def test_probe_battery_ok(self):
        payload = b"\x01" + bytes(4) + bytes(13) + b"\x00\x00\x00"
        result = self._parse(
            manufacturer_data=_mfr(payload),
            service_uuids=[COMBUSTION_SERVICE_UUID],
        )
        assert result.metadata["battery_low"] is False

    def test_probe_hop_count(self):
        payload = b"\x01" + bytes(4) + bytes(13) + b"\x00\x00\x05"
        result = self._parse(
            manufacturer_data=_mfr(payload),
            service_uuids=[COMBUSTION_SERVICE_UUID],
        )
        assert result.metadata["hop_count"] == 5

    def test_node_uses_probe_layout(self):
        # NODE (0x02) is a relay — same first 21 bytes as a probe.
        serial = struct.pack("<I", 0xDEADBEEF)
        payload = b"\x02" + serial + bytes(13) + b"\x00\x00\x01"
        result = self._parse(
            manufacturer_data=_mfr(payload),
            service_uuids=[COMBUSTION_SERVICE_UUID],
        )
        assert result.metadata["product_type"] == "NODE"
        assert result.metadata["serial_number"] == 0xDEADBEEF
        assert result.metadata["hop_count"] == 1


class TestGaugeParsing:
    def _parse(self, **kwargs):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(**kwargs)
        matched = registry.match(ad)
        assert matched
        return matched[0].parse(ad)

    def test_gauge_extracts_serial(self):
        # product=0x03, serial=10 ASCII bytes, temp=2 bytes, status=1, reserved=1, alarms=4
        serial = b"GAUGE12345"
        temp_bytes = struct.pack("<H", 1000)  # raw 1000 -> 30 C
        payload = b"\x03" + serial + temp_bytes + b"\x00\x00" + bytes(4)
        assert len(payload) == 19
        result = self._parse(
            manufacturer_data=_mfr(payload),
            service_uuids=[COMBUSTION_SERVICE_UUID],
        )
        assert result.metadata["product_type"] == "GAUGE"
        assert result.metadata["serial_ascii"] == "GAUGE12345"
        assert result.metadata["temperature_c"] == pytest.approx(30.0)


class TestDFUMode:
    def _parse(self, **kwargs):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(**kwargs)
        matched = registry.match(ad)
        assert matched
        return matched[0].parse(ad)

    def test_dfu_name_extracts_class_and_serial_suffix(self):
        result = self._parse(local_name="Thermom_DFU_ABC123")
        assert result.metadata["dfu_mode"] is True
        assert result.metadata["dfu_class"] == "Probe"
        assert result.metadata["dfu_suffix"] == "ABC123"

    def test_dfu_legacy_name(self):
        result = self._parse(local_name="CI Probe BL")
        assert result.metadata["dfu_mode"] is True
        assert result.metadata["dfu_class"] == "Probe"
        assert result.metadata["dfu_legacy"] is True


class TestIdentity:
    def _parse(self, **kwargs):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(**kwargs)
        matched = registry.match(ad)
        assert matched
        return matched[0].parse(ad)

    def test_probe_identity_uses_serial(self):
        serial = struct.pack("<I", 0xCAFEBABE)
        payload = b"\x01" + serial + bytes(16)
        result = self._parse(
            manufacturer_data=_mfr(payload),
            service_uuids=[COMBUSTION_SERVICE_UUID],
            mac_address="11:22:33:44:55:66",
        )
        expected = hashlib.sha256(b"combustion:probe:3405691582").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_gauge_identity_uses_ascii_serial(self):
        serial = b"GAUGEAAAAA"
        payload = b"\x03" + serial + bytes(8)
        result = self._parse(
            manufacturer_data=_mfr(payload),
            service_uuids=[COMBUSTION_SERVICE_UUID],
        )
        expected = hashlib.sha256(b"combustion:gauge:GAUGEAAAAA").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_parse_result_basics(self):
        payload = b"\x01" + bytes(20)
        result = self._parse(
            manufacturer_data=_mfr(payload),
            service_uuids=[COMBUSTION_SERVICE_UUID],
        )
        assert result.parser_name == "combustion"
        assert result.beacon_type == "combustion"
        assert result.device_class == "sensor"
