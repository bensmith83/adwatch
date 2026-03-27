"""Tests for b-parasite soil sensor plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

# RED phase — this import will fail until the plugin exists
from adwatch.plugins.b_parasite import BParasiteParser, BPARASITE_UUID


def _make_ad(**kwargs):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "random",
        "manufacturer_data": None,
        "service_data": None,
        "local_name": None,
    }
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _build_service_data(
    version=2,
    has_light=False,
    counter=0,
    battery_mv=3000,
    temp_c=25.0,
    humidity_pct=50.0,
    soil_pct=40.0,
    mac=b"\xAA\xBB\xCC\xDD\xEE\xFF",
    illuminance=500,
):
    """Build b-parasite v2 service data (18 bytes, no UUID prefix)."""
    proto = (version << 4) | (0x01 if has_light else 0x00)
    data = struct.pack("B", proto)
    data += struct.pack("B", counter & 0x0F)
    data += struct.pack(">H", battery_mv)
    temp_raw = int(temp_c * 100)
    data += struct.pack(">h", temp_raw)
    hum_raw = int(humidity_pct / 100.0 * 65535)
    data += struct.pack(">H", hum_raw)
    soil_raw = int(soil_pct / 100.0 * 65535)
    data += struct.pack(">H", soil_raw)
    data += mac
    data += struct.pack(">H", illuminance)
    return data


def _make_registry_and_parser():
    registry = ParserRegistry()

    @register_parser(
        name="b_parasite",
        service_uuid=BPARASITE_UUID,
        local_name_pattern=r"^prst",
        description="b-parasite soil sensor",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(BParasiteParser):
        pass

    return registry


class TestBParasiteParser:
    def test_valid_v2_parses_all_fields(self):
        """Valid v2 service data parses temperature, humidity, soil moisture, battery."""
        registry = _make_registry_and_parser()
        data = _build_service_data(
            battery_mv=3100, temp_c=22.5, humidity_pct=60.0, soil_pct=45.0
        )
        ad = _make_ad(service_data={BPARASITE_UUID: data})
        matches = registry.match(ad)
        assert len(matches) == 1
        result = matches[0].parse(ad)
        assert result is not None
        assert result.parser_name == "b_parasite"
        assert result.beacon_type == "b_parasite"
        assert result.device_class == "sensor"
        assert result.metadata["battery_mv"] == 3100
        assert result.metadata["temperature_c"] == 22.5
        assert abs(result.metadata["humidity_percent"] - 60.0) < 0.01
        assert abs(result.metadata["soil_moisture_percent"] - 45.0) < 0.01

    def test_illuminance_when_has_light_set(self):
        """Illuminance parsed when has_light bit set and data long enough."""
        registry = _make_registry_and_parser()
        data = _build_service_data(has_light=True, illuminance=1234)
        ad = _make_ad(service_data={BPARASITE_UUID: data})
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.metadata["illuminance"] == 1234

    def test_no_illuminance_when_has_light_not_set(self):
        """Illuminance NOT in metadata when has_light bit not set."""
        registry = _make_registry_and_parser()
        data = _build_service_data(has_light=False, illuminance=1234)
        ad = _make_ad(service_data={BPARASITE_UUID: data})
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert "illuminance" not in result.metadata

    def test_wrong_version_returns_none(self):
        """Version != 2 returns None."""
        registry = _make_registry_and_parser()
        data = _build_service_data(version=1)
        ad = _make_ad(service_data={BPARASITE_UUID: data})
        result = registry.match(ad)[0].parse(ad)
        assert result is None

    def test_too_short_data_returns_none(self):
        """Too-short service data returns None."""
        registry = _make_registry_and_parser()
        ad = _make_ad(service_data={BPARASITE_UUID: bytes(5)})
        result = registry.match(ad)[0].parse(ad)
        assert result is None

    def test_local_name_presence_only(self):
        """Local name 'prst' without service data returns presence_only result."""
        registry = _make_registry_and_parser()
        ad = _make_ad(local_name="prst:soil-1")
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.metadata["presence_only"] is True
        assert result.parser_name == "b_parasite"

    def test_identity_hash_based_on_mac(self):
        """Identity hash based on MAC address."""
        registry = _make_registry_and_parser()
        mac = "11:22:33:44:55:66"
        data = _build_service_data()
        ad = _make_ad(mac_address=mac, service_data={BPARASITE_UUID: data})
        result = registry.match(ad)[0].parse(ad)
        expected = hashlib.sha256(mac.encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_no_matching_data_returns_none(self):
        """No matching data returns None."""
        registry = _make_registry_and_parser()
        ad = _make_ad()  # no service_data, no local_name
        # Won't match registry at all, so test the parser directly
        parser = BParasiteParser()
        result = parser.parse(ad)
        assert result is None
