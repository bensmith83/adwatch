"""Tests for Ember Mug heated mug plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

# RED phase — this import will fail until the plugin exists
from adwatch.plugins.ember_mug import EmberMugParser


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


def _build_ember_mfr_data(header=0x00, model_id=1, generation=2, color_id=1):
    """Build Ember mfr data: company_id(2) + header(1) + model_id(1) + gen(1) + color(1)."""
    data = struct.pack("<H", 0x03C1)  # company_id
    data += bytes([header, model_id, generation, color_id])
    return data


def _build_ember_short_mfr_data(model_id_int):
    """Build short-format Ember mfr data: company_id(2) + big-endian model int."""
    data = struct.pack("<H", 0x03C1)
    data += model_id_int.to_bytes(2, "big", signed=True)
    return data


class TestEmberMugParser:
    def test_company_id_match(self):
        """Should match company ID 0x03C1."""
        registry = ParserRegistry()

        @register_parser(
            name="ember_mug", company_id=0x03C1, local_name_pattern=r"^Ember",
            description="Ember Mug", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(EmberMugParser):
            pass

        mfr_data = _build_ember_mfr_data()
        ad = _make_ad(manufacturer_data=mfr_data)
        assert len(registry.match(ad)) == 1

    def test_extended_format_model_extraction(self):
        """Extended format (≥4 payload bytes): model_id, generation, color_id extraction."""
        registry = ParserRegistry()

        @register_parser(
            name="ember_mug", company_id=0x03C1, local_name_pattern=r"^Ember",
            description="Ember Mug", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(EmberMugParser):
            pass

        mfr_data = _build_ember_mfr_data(model_id=2, generation=3, color_id=2)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.metadata["model_id"] == 2
        assert result.metadata["generation"] == 3
        assert result.metadata["color_id"] == 2

    def test_model_mug_10oz(self):
        """Model ID 1 with gen≥2 → 'Mug 2 (10oz)'."""
        registry = ParserRegistry()

        @register_parser(
            name="ember_mug", company_id=0x03C1, local_name_pattern=r"^Ember",
            description="Ember Mug", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(EmberMugParser):
            pass

        mfr_data = _build_ember_mfr_data(model_id=1, generation=2)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert "Mug" in result.metadata["model_name"]
        assert "10oz" in result.metadata["model_name"]

    def test_model_mug_14oz(self):
        """Model ID 2 → Mug 14oz."""
        registry = ParserRegistry()

        @register_parser(
            name="ember_mug", company_id=0x03C1, local_name_pattern=r"^Ember",
            description="Ember Mug", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(EmberMugParser):
            pass

        mfr_data = _build_ember_mfr_data(model_id=2, generation=2)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert "14oz" in result.metadata["model_name"]

    def test_model_travel_mug(self):
        """Model ID 3 → Travel Mug."""
        registry = ParserRegistry()

        @register_parser(
            name="ember_mug", company_id=0x03C1, local_name_pattern=r"^Ember",
            description="Ember Mug", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(EmberMugParser):
            pass

        mfr_data = _build_ember_mfr_data(model_id=3, generation=2)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert "Travel Mug" in result.metadata["model_name"]

    def test_model_cup_6oz(self):
        """Model ID 8 → Cup 6oz."""
        registry = ParserRegistry()

        @register_parser(
            name="ember_mug", company_id=0x03C1, local_name_pattern=r"^Ember",
            description="Ember Mug", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(EmberMugParser):
            pass

        mfr_data = _build_ember_mfr_data(model_id=8, generation=2)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert "Cup" in result.metadata["model_name"]
        assert "6oz" in result.metadata["model_name"]

    def test_model_tumbler_16oz(self):
        """Model ID 9 → Tumbler 16oz."""
        registry = ParserRegistry()

        @register_parser(
            name="ember_mug", company_id=0x03C1, local_name_pattern=r"^Ember",
            description="Ember Mug", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(EmberMugParser):
            pass

        mfr_data = _build_ember_mfr_data(model_id=9, generation=2)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert "Tumbler" in result.metadata["model_name"]
        assert "16oz" in result.metadata["model_name"]

    def test_gen1_naming(self):
        """Gen < 2 → Gen 1 naming (e.g., 'Mug (10oz)' not 'Mug 2 (10oz)')."""
        registry = ParserRegistry()

        @register_parser(
            name="ember_mug", company_id=0x03C1, local_name_pattern=r"^Ember",
            description="Ember Mug", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(EmberMugParser):
            pass

        mfr_data = _build_ember_mfr_data(model_id=1, generation=1)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert "2" not in result.metadata["model_name"]
        assert "10oz" in result.metadata["model_name"]

    def test_gen2_naming(self):
        """Gen ≥ 2 → Gen 2 naming (e.g., 'Mug 2 (10oz)')."""
        registry = ParserRegistry()

        @register_parser(
            name="ember_mug", company_id=0x03C1, local_name_pattern=r"^Ember",
            description="Ember Mug", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(EmberMugParser):
            pass

        mfr_data = _build_ember_mfr_data(model_id=1, generation=2)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert "2" in result.metadata["model_name"]

    def test_color_lookup(self):
        """Color ID should be looked up to a color name."""
        registry = ParserRegistry()

        @register_parser(
            name="ember_mug", company_id=0x03C1, local_name_pattern=r"^Ember",
            description="Ember Mug", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(EmberMugParser):
            pass

        # Color ID 1 = Black
        mfr_data = _build_ember_mfr_data(color_id=1)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert "color" in result.metadata

    def test_short_format(self):
        """Short format (< 4 payload bytes): model_id from big-endian int."""
        registry = ParserRegistry()

        @register_parser(
            name="ember_mug", company_id=0x03C1, local_name_pattern=r"^Ember",
            description="Ember Mug", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(EmberMugParser):
            pass

        mfr_data = _build_ember_short_mfr_data(1)
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.metadata["model_id"] == 1

    def test_match_by_local_name(self):
        """Should match by local_name starting with 'Ember'."""
        registry = ParserRegistry()

        @register_parser(
            name="ember_mug", company_id=0x03C1, local_name_pattern=r"^Ember",
            description="Ember Mug", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(EmberMugParser):
            pass

        ad = _make_ad(local_name="Ember Device")
        assert len(registry.match(ad)) == 1

    def test_identity_hash(self):
        """Identity hash: SHA256('{mac}:Ember')[:16]."""
        registry = ParserRegistry()

        @register_parser(
            name="ember_mug", company_id=0x03C1, local_name_pattern=r"^Ember",
            description="Ember Mug", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(EmberMugParser):
            pass

        mfr_data = _build_ember_mfr_data()
        ad = _make_ad(manufacturer_data=mfr_data, mac_address="11:22:33:44:55:66")
        result = registry.match(ad)[0].parse(ad)
        expected = hashlib.sha256("11:22:33:44:55:66:Ember".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_device_class(self):
        """Device class should be 'mug' or 'drinkware'."""
        registry = ParserRegistry()

        @register_parser(
            name="ember_mug", company_id=0x03C1, local_name_pattern=r"^Ember",
            description="Ember Mug", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(EmberMugParser):
            pass

        mfr_data = _build_ember_mfr_data()
        ad = _make_ad(manufacturer_data=mfr_data)
        result = registry.match(ad)[0].parse(ad)
        assert result.device_class in ("mug", "drinkware")


class TestEmberMugServiceUUID:
    """Service UUID matching per apk-ble-hunting/reports/embertech_passive.md."""

    def _register(self, registry):
        from adwatch.plugins.ember_mug import (
            EMBER_SERVICE_UUID_ORIGINAL,
            EMBER_SERVICE_UUID_CERAMIC,
        )

        @register_parser(
            name="ember_mug",
            company_id=0x03C1,
            service_uuid=[EMBER_SERVICE_UUID_ORIGINAL, EMBER_SERVICE_UUID_CERAMIC],
            local_name_pattern=r"^Ember",
            description="Ember Mug",
            version="1.1.0",
            core=False,
            registry=registry,
        )
        class _P(EmberMugParser):
            pass

    def test_matches_original_service_uuid(self):
        from adwatch.plugins.ember_mug import EMBER_SERVICE_UUID_ORIGINAL
        registry = ParserRegistry()
        self._register(registry)
        ad = _make_ad(service_uuids=[EMBER_SERVICE_UUID_ORIGINAL])
        assert len(registry.match(ad)) == 1

    def test_matches_ceramic_service_uuid(self):
        from adwatch.plugins.ember_mug import EMBER_SERVICE_UUID_CERAMIC
        registry = ParserRegistry()
        self._register(registry)
        ad = _make_ad(service_uuids=[EMBER_SERVICE_UUID_CERAMIC])
        assert len(registry.match(ad)) == 1

    def test_service_generation_tagged_from_uuid(self):
        from adwatch.plugins.ember_mug import (
            EmberMugParser,
            EMBER_SERVICE_UUID_CERAMIC,
        )
        registry = ParserRegistry()
        self._register(registry)
        ad = _make_ad(service_uuids=[EMBER_SERVICE_UUID_CERAMIC])
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.metadata["service_generation"] == "ceramic_mug"

    def test_dfu_mode_detected_from_nordic_uuid(self):
        from adwatch.plugins.ember_mug import (
            EMBER_SERVICE_UUID_ORIGINAL,
            NORDIC_DFU_SERVICE_UUID,
        )
        registry = ParserRegistry()
        self._register(registry)
        ad = _make_ad(
            service_uuids=[EMBER_SERVICE_UUID_ORIGINAL, NORDIC_DFU_SERVICE_UUID]
        )
        result = registry.match(ad)[0].parse(ad)
        assert result.metadata["dfu_mode"] is True
