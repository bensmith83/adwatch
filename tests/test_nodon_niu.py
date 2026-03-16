"""Tests for NodOn NIU smart button plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser


def _make_ad(**kwargs):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "random",
        "manufacturer_data": None,
        "service_data": None,
        "local_name": "NIU",
    }
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _build_mfr_data(button_event, color, battery, company_id=0x0000):
    """Build manufacturer_data: company_id(LE) + event + color + battery."""
    import struct
    return struct.pack("<H", company_id) + bytes([button_event, color, battery])


class TestNodOnNiuParser:
    def _registry_and_parser(self):
        from adwatch.plugins.nodon_niu import NodOnNiuParser

        registry = ParserRegistry()

        @register_parser(
            name="nodon_niu",
            local_name_pattern=r"NIU",
            description="NodOn NIU smart button",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class TestParser(NodOnNiuParser):
            pass

        return registry

    def test_match_by_local_name(self):
        """Should match advertisements with local_name containing NIU."""
        registry = self._registry_and_parser()
        ad = _make_ad(
            manufacturer_data=_build_mfr_data(0x01, 0x01, 80),
            local_name="NIU",
        )
        assert len(registry.match(ad)) == 1

    def test_match_local_name_with_prefix(self):
        """Should match local_name like 'MyNIU-button'."""
        registry = self._registry_and_parser()
        ad = _make_ad(
            manufacturer_data=_build_mfr_data(0x01, 0x01, 80),
            local_name="MyNIU-button",
        )
        assert len(registry.match(ad)) == 1

    def test_single_press(self):
        """Button event 0x01 = single press."""
        registry = self._registry_and_parser()
        ad = _make_ad(manufacturer_data=_build_mfr_data(0x01, 0x01, 95))
        result = registry.match(ad)[0].parse(ad)

        assert result is not None
        assert result.parser_name == "nodon_niu"
        assert result.beacon_type == "nodon_niu"
        assert result.device_class == "sensor"
        assert result.metadata["button_event"] == "single"
        assert result.metadata["button_color"] == "white"
        assert result.metadata["battery"] == 95

    def test_double_press(self):
        """Button event 0x02 = double press."""
        registry = self._registry_and_parser()
        ad = _make_ad(manufacturer_data=_build_mfr_data(0x02, 0x02, 80))
        result = registry.match(ad)[0].parse(ad)

        assert result.metadata["button_event"] == "double"
        assert result.metadata["button_color"] == "blue"

    def test_triple_press(self):
        """Button event 0x03 = triple press."""
        registry = self._registry_and_parser()
        ad = _make_ad(manufacturer_data=_build_mfr_data(0x03, 0x03, 70))
        result = registry.match(ad)[0].parse(ad)

        assert result.metadata["button_event"] == "triple"
        assert result.metadata["button_color"] == "green"

    def test_quad_press(self):
        """Button event 0x04 = quad press."""
        registry = self._registry_and_parser()
        ad = _make_ad(manufacturer_data=_build_mfr_data(0x04, 0x04, 60))
        result = registry.match(ad)[0].parse(ad)

        assert result.metadata["button_event"] == "quad"
        assert result.metadata["button_color"] == "red"

    def test_quintuple_press(self):
        """Button event 0x05 = quintuple press."""
        registry = self._registry_and_parser()
        ad = _make_ad(manufacturer_data=_build_mfr_data(0x05, 0x05, 50))
        result = registry.match(ad)[0].parse(ad)

        assert result.metadata["button_event"] == "quintuple"
        assert result.metadata["button_color"] == "black"

    def test_long_press(self):
        """Button event 0x09 = long_press."""
        registry = self._registry_and_parser()
        ad = _make_ad(manufacturer_data=_build_mfr_data(0x09, 0x01, 90))
        result = registry.match(ad)[0].parse(ad)

        assert result.metadata["button_event"] == "long_press"

    def test_release(self):
        """Button event 0x0A = release."""
        registry = self._registry_and_parser()
        ad = _make_ad(manufacturer_data=_build_mfr_data(0x0A, 0x01, 85))
        result = registry.match(ad)[0].parse(ad)

        assert result.metadata["button_event"] == "release"

    def test_unknown_button_event(self):
        """Unknown button event returns None."""
        registry = self._registry_and_parser()
        ad = _make_ad(manufacturer_data=_build_mfr_data(0xFF, 0x01, 80))
        result = registry.match(ad)[0].parse(ad)

        assert result is None

    def test_unknown_color(self):
        """Unknown color code returns None."""
        registry = self._registry_and_parser()
        ad = _make_ad(manufacturer_data=_build_mfr_data(0x01, 0xFF, 80))
        result = registry.match(ad)[0].parse(ad)

        assert result is None

    def test_no_manufacturer_data(self):
        """No manufacturer data returns None."""
        from adwatch.plugins.nodon_niu import NodOnNiuParser
        parser = NodOnNiuParser()
        ad = _make_ad(manufacturer_data=None)
        assert parser.parse(ad) is None

    def test_too_short_data(self):
        """Manufacturer data too short returns None."""
        from adwatch.plugins.nodon_niu import NodOnNiuParser
        parser = NodOnNiuParser()
        ad = _make_ad(manufacturer_data=b"\x00\x00\x01\x01")  # only 2 bytes payload
        assert parser.parse(ad) is None

    def test_identity_hash(self):
        """Identity hash: SHA256('{mac}:nodon_niu')[:16]."""
        registry = self._registry_and_parser()
        ad = _make_ad(
            manufacturer_data=_build_mfr_data(0x01, 0x01, 80),
            mac_address="11:22:33:44:55:66",
        )
        result = registry.match(ad)[0].parse(ad)

        expected = hashlib.sha256("11:22:33:44:55:66:nodon_niu".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_raw_payload_hex(self):
        """raw_payload_hex contains the payload bytes in hex."""
        registry = self._registry_and_parser()
        ad = _make_ad(manufacturer_data=_build_mfr_data(0x01, 0x02, 99))
        result = registry.match(ad)[0].parse(ad)

        assert result.raw_payload_hex == "010263"

    def test_battery_zero(self):
        """Battery 0% is valid."""
        registry = self._registry_and_parser()
        ad = _make_ad(manufacturer_data=_build_mfr_data(0x01, 0x01, 0))
        result = registry.match(ad)[0].parse(ad)

        assert result.metadata["battery"] == 0

    def test_battery_100(self):
        """Battery 100% is valid."""
        registry = self._registry_and_parser()
        ad = _make_ad(manufacturer_data=_build_mfr_data(0x01, 0x01, 100))
        result = registry.match(ad)[0].parse(ad)

        assert result.metadata["battery"] == 100
