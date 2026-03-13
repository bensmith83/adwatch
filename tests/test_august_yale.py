"""Tests for August/Yale smart lock plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

# RED phase — this import will fail until the plugin exists
from adwatch.plugins.august_yale import AugustYaleParser


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


def _build_august_mfr_data(company_id=0x01D1, toggle=0x00):
    """Build August/Yale mfr data: company_id(2) + toggle(1)."""
    return struct.pack("<H", company_id) + bytes([toggle])


class TestAugustYaleParser:
    def test_match_august_company_id(self):
        """Should match company_id 0x01D1 (August)."""
        registry = ParserRegistry()

        @register_parser(
            name="august_yale", company_id=[0x01D1, 0x012E, 0x0BDE],
            service_uuid="fe24",
            description="August/Yale", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(AugustYaleParser):
            pass

        mfr_data = _build_august_mfr_data(company_id=0x01D1)
        ad = _make_ad(manufacturer_data=mfr_data)
        assert len(registry.match(ad)) == 1

    def test_match_assa_abloy_company_id(self):
        """Should match company_id 0x012E (ASSA ABLOY)."""
        registry = ParserRegistry()

        @register_parser(
            name="august_yale", company_id=[0x01D1, 0x012E, 0x0BDE],
            service_uuid="fe24",
            description="August/Yale", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(AugustYaleParser):
            pass

        mfr_data = _build_august_mfr_data(company_id=0x012E)
        ad = _make_ad(manufacturer_data=mfr_data)
        assert len(registry.match(ad)) == 1

    def test_match_yale_company_id(self):
        """Should match company_id 0x0BDE (Yale)."""
        registry = ParserRegistry()

        @register_parser(
            name="august_yale", company_id=[0x01D1, 0x012E, 0x0BDE],
            service_uuid="fe24",
            description="August/Yale", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(AugustYaleParser):
            pass

        mfr_data = _build_august_mfr_data(company_id=0x0BDE)
        ad = _make_ad(manufacturer_data=mfr_data)
        assert len(registry.match(ad)) == 1

    def test_match_service_uuid_fe24(self):
        """Should match by service_uuid 0xFE24."""
        registry = ParserRegistry()

        @register_parser(
            name="august_yale", company_id=[0x01D1, 0x012E, 0x0BDE],
            service_uuid="fe24",
            description="August/Yale", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(AugustYaleParser):
            pass

        ad = _make_ad(service_uuids=["fe24"])
        assert len(registry.match(ad)) == 1

    def test_toggle_byte_extraction(self):
        """Toggle byte (0 or 1) should be extracted from mfr_data."""
        registry = ParserRegistry()

        @register_parser(
            name="august_yale", company_id=[0x01D1, 0x012E, 0x0BDE],
            service_uuid="fe24",
            description="August/Yale", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(AugustYaleParser):
            pass

        # Toggle = 0
        mfr_data = _build_august_mfr_data(toggle=0)
        ad = _make_ad(manufacturer_data=mfr_data, local_name="A112345")
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.metadata["state_toggle"] == 0

        # Toggle = 1
        mfr_data = _build_august_mfr_data(toggle=1)
        ad = _make_ad(manufacturer_data=mfr_data, local_name="A112345")
        result = registry.match(ad)[0].parse(ad)
        assert result.metadata["state_toggle"] == 1

    def test_identity_hash(self):
        """Identity hash: SHA256('{mac}:{local_name}')[:16]."""
        registry = ParserRegistry()

        @register_parser(
            name="august_yale", company_id=[0x01D1, 0x012E, 0x0BDE],
            service_uuid="fe24",
            description="August/Yale", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(AugustYaleParser):
            pass

        mfr_data = _build_august_mfr_data()
        ad = _make_ad(
            manufacturer_data=mfr_data,
            mac_address="11:22:33:44:55:66",
            local_name="A112345",
        )
        result = registry.match(ad)[0].parse(ad)
        expected = hashlib.sha256("11:22:33:44:55:66:A112345".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_device_class(self):
        """Device class should be 'lock'."""
        registry = ParserRegistry()

        @register_parser(
            name="august_yale", company_id=[0x01D1, 0x012E, 0x0BDE],
            service_uuid="fe24",
            description="August/Yale", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(AugustYaleParser):
            pass

        mfr_data = _build_august_mfr_data()
        ad = _make_ad(manufacturer_data=mfr_data, local_name="A112345")
        result = registry.match(ad)[0].parse(ad)
        assert result.device_class == "lock"

    def test_beacon_type(self):
        """Beacon type should be 'august_yale'."""
        registry = ParserRegistry()

        @register_parser(
            name="august_yale", company_id=[0x01D1, 0x012E, 0x0BDE],
            service_uuid="fe24",
            description="August/Yale", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(AugustYaleParser):
            pass

        mfr_data = _build_august_mfr_data()
        ad = _make_ad(manufacturer_data=mfr_data, local_name="A112345")
        result = registry.match(ad)[0].parse(ad)
        assert result.beacon_type == "august_yale"
