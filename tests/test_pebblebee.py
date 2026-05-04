"""Tests for Pebblebee tracker plugin."""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.pebblebee import (
    PebblebeeParser,
    PEBBLEBEE_FINDER_CID,
    PEBBLEBEE_R4K_CID,
    FINDER_SERVICE_UUID,
    R4K_SERVICE_UUID,
)


def _make_ad(**kw):
    defaults = {"timestamp": "2025-01-01T00:00:00Z", "mac_address": "AA:BB:CC:DD:EE:FF",
                "address_type": "random", "manufacturer_data": None, "service_data": None}
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _finder_mfr(type_byte=0x01, payload=b"\x00\x00\x00\x00\x00\x00\x00"):
    return (PEBBLEBEE_FINDER_CID).to_bytes(2, "little") + bytes([type_byte]) + payload


def _r4k_mfr(type_byte=0x05, payload=b"\x00\x00\x00\x00\x00\x00\x00"):
    return (PEBBLEBEE_R4K_CID).to_bytes(2, "little") + bytes([type_byte]) + payload


def _register(registry):
    @register_parser(name="pebblebee",
                     company_id=[PEBBLEBEE_FINDER_CID, PEBBLEBEE_R4K_CID],
                     service_uuid=[FINDER_SERVICE_UUID, R4K_SERVICE_UUID],
                     local_name_pattern=r"^PebbleBee$",
                     description="Pebblebee", version="1.0.0", core=False,
                     registry=registry)
    class _P(PebblebeeParser):
        pass
    return _P


class TestPebblebeeMatching:
    def test_match_finder_cid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=_finder_mfr())
        assert len(registry.match(ad)) == 1

    def test_match_r4k_cid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=_r4k_mfr())
        assert len(registry.match(ad)) == 1

    def test_match_finder_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[FINDER_SERVICE_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_r4k_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[R4K_SERVICE_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_honey_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="PebbleBee")
        assert len(registry.match(ad)) == 1


class TestPebblebeeParsing:
    def test_finder_family_tag(self):
        ad = _make_ad(manufacturer_data=_finder_mfr())
        result = PebblebeeParser().parse(ad)
        assert result is not None
        assert result.metadata["product_family"] == "Finder"

    def test_r4k_family_tag(self):
        ad = _make_ad(manufacturer_data=_r4k_mfr())
        result = PebblebeeParser().parse(ad)
        assert result.metadata["product_family"] == "R4K"

    def test_honey_family_tag(self):
        ad = _make_ad(local_name="PebbleBee")
        result = PebblebeeParser().parse(ad)
        assert result.metadata["product_family"] == "Honey"

    def test_finder_type_byte_extracted(self):
        ad = _make_ad(manufacturer_data=_finder_mfr(type_byte=0x07))
        result = PebblebeeParser().parse(ad)
        assert result.metadata["type_discriminator"] == 0x07

    def test_r4k_type_byte_extracted(self):
        ad = _make_ad(manufacturer_data=_r4k_mfr(type_byte=0x42))
        result = PebblebeeParser().parse(ad)
        assert result.metadata["type_discriminator"] == 0x42

    def test_finder_uuid_only_no_type(self):
        ad = _make_ad(service_uuids=[FINDER_SERVICE_UUID])
        result = PebblebeeParser().parse(ad)
        assert result.metadata["product_family"] == "Finder"
        assert "type_discriminator" not in result.metadata

    def test_basics(self):
        result = PebblebeeParser().parse(_make_ad(manufacturer_data=_finder_mfr()))
        assert result.parser_name == "pebblebee"
        assert result.beacon_type == "pebblebee"
        assert result.device_class == "tracker"

    def test_returns_none_unrelated(self):
        assert PebblebeeParser().parse(_make_ad(local_name="Other")) is None
