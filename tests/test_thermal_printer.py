"""Tests for BLE thermal printer (cat printer / GOOJPRT / PeriPage) parser."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.thermal_printer import (
    ThermalPrinterParser,
    PRINTER_SERVICE_UUID,
    PRINTER_DFU_UUID,
)


def _make_ad(**kwargs):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "public",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _make_registry():
    registry = ParserRegistry()

    @register_parser(
        name="thermal_printer",
        service_uuid=[PRINTER_SERVICE_UUID, PRINTER_DFU_UUID],
        local_name_pattern=r"^(GB0[123]|GT0[12]|MX0[0-9]|PT-?2[01]0|MTP-?[23]|PeriPage|YT01|GLI\d{3,4})",
        description="BLE thermal / receipt printer (cat printer, GOOJPRT, PeriPage)",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(ThermalPrinterParser):
        pass

    return registry


class TestThermalPrinterRegistry:
    def test_matches_custom_service_uuid(self):
        """Matches on the vendor 128-bit UUID shared by cat-printer firmwares."""
        registry = _make_registry()
        ad = _make_ad(service_uuids=[PRINTER_SERVICE_UUID])
        assert len(registry.match(ad)) >= 1

    def test_matches_on_dfu_uuid_with_known_name(self):
        """Matches on DFU UUID 18F0 + recognizable GLI1050 product name."""
        registry = _make_registry()
        ad = _make_ad(service_uuids=["18f0"], local_name="GLI1050.I")
        assert len(registry.match(ad)) >= 1

    def test_matches_common_cat_printer_names(self):
        """GB01/GB02/GB03 are the archetypal cat-printer model names."""
        registry = _make_registry()
        for name in ("GB01", "GB02", "GB03", "GT01", "MX05", "PeriPage A6"):
            ad = _make_ad(local_name=name)
            assert len(registry.match(ad)) >= 1, f"no match for {name}"

    def test_no_match_unrelated(self):
        registry = _make_registry()
        ad = _make_ad(local_name="SomeRandomDevice")
        assert len(registry.match(ad)) == 0


class TestThermalPrinterParser:
    def test_parser_name_and_class(self):
        parser = ThermalPrinterParser()
        ad = _make_ad(local_name="GLI1050.I", service_uuids=["18f0"])
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "thermal_printer"
        assert result.beacon_type == "thermal_printer"
        assert result.device_class == "printer"

    def test_model_detected_from_name(self):
        parser = ThermalPrinterParser()
        ad = _make_ad(local_name="GLI1050.I")
        result = parser.parse(ad)
        assert result.metadata.get("model") == "GLI1050"
        assert result.metadata.get("device_name") == "GLI1050.I"

    def test_model_from_cat_printer_name(self):
        parser = ThermalPrinterParser()
        ad = _make_ad(local_name="GB03")
        result = parser.parse(ad)
        assert result.metadata.get("model") == "GB03"

    def test_matches_by_custom_uuid_only(self):
        """No local name, but custom printer UUID present → still parses."""
        parser = ThermalPrinterParser()
        ad = _make_ad(service_uuids=[PRINTER_SERVICE_UUID])
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "thermal_printer"

    def test_identity_hash_stable(self):
        mac = "11:22:33:44:55:66"
        parser = ThermalPrinterParser()
        ad = _make_ad(mac_address=mac, local_name="GLI1050.I")
        result = parser.parse(ad)
        expected = hashlib.sha256(f"{mac}:thermal_printer".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_returns_none_for_unrelated(self):
        parser = ThermalPrinterParser()
        ad = _make_ad(local_name="SomeOtherThing")
        assert parser.parse(ad) is None

    def test_dfu_uuid_alone_not_enough(self):
        """18F0 is the generic Nordic DFU UUID; it alone must not match —
        many non-printer devices advertise it. Require name or custom UUID."""
        parser = ThermalPrinterParser()
        ad = _make_ad(service_uuids=["18f0"])
        assert parser.parse(ad) is None
