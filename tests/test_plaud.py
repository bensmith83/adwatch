"""Tests for PLAUD AI recorder BLE advertisement plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.plaud import PlaudParser, PLAUD_NAME_RE


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


def _make_registry():
    registry = ParserRegistry()

    @register_parser(
        name="plaud",
        local_name_pattern=r"^PLAUD[\s_]",
        description="PLAUD AI recorder advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(PlaudParser):
        pass

    return registry


class TestPlaudMatching:
    def test_matches_plaud_note_name(self):
        """Matches on PLAUD_NOTE local name."""
        registry = _make_registry()
        ad = _make_ad(local_name="PLAUD_NOTE")
        matches = registry.match(ad)
        assert len(matches) == 1

    def test_matches_plaud_notepin_name(self):
        """Matches on 'PLAUD NotePin' local name."""
        registry = _make_registry()
        ad = _make_ad(local_name="PLAUD NotePin")
        matches = registry.match(ad)
        assert len(matches) == 1

    def test_no_match_without_plaud_name(self):
        """Does not match unrelated devices."""
        parser = PlaudParser()
        ad = _make_ad(local_name="SomeDevice")
        result = parser.parse(ad)
        assert result is None

    def test_no_match_without_name(self):
        """Does not match when no local name."""
        parser = PlaudParser()
        ad = _make_ad()
        result = parser.parse(ad)
        assert result is None


class TestPlaudParsing:
    def test_parse_plaud_note_with_mfr_data(self):
        """Parses PLAUD NOTE with manufacturer data."""
        parser = PlaudParser()
        mfr = bytes.fromhex("590002780304565f0000098883163743897198850a0004f578ed1e0101")
        ad = _make_ad(local_name="PLAUD_NOTE", manufacturer_data=mfr)
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "plaud"
        assert result.beacon_type == "plaud"
        assert result.device_class == "recorder"
        assert result.metadata["model"] == "NOTE"

    def test_parse_plaud_notepin_with_mfr_data(self):
        """Parses PLAUD NotePin with manufacturer data."""
        parser = PlaudParser()
        mfr = bytes.fromhex("5d000456d50000088800040122736261440a0004001828570101")
        ad = _make_ad(local_name="PLAUD NotePin", manufacturer_data=mfr)
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["model"] == "NotePin"

    def test_parse_plaud_note_without_mfr_data(self):
        """Parses PLAUD NOTE even without manufacturer data (name-only ad)."""
        parser = PlaudParser()
        ad = _make_ad(local_name="PLAUD_NOTE")
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["model"] == "NOTE"
        assert result.metadata["device_name"] == "PLAUD_NOTE"

    def test_identity_hash(self):
        """Identity hash is SHA256('plaud:{mac}')[:16]."""
        mac = "11:22:33:44:55:66"
        parser = PlaudParser()
        ad = _make_ad(local_name="PLAUD_NOTE", mac_address=mac)
        result = parser.parse(ad)
        expected = hashlib.sha256(f"plaud:{mac}".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_raw_payload_hex(self):
        """raw_payload_hex contains manufacturer data when present."""
        parser = PlaudParser()
        mfr = bytes.fromhex("590002780304565f0000098883163743897198850a0004f578ed1e0101")
        ad = _make_ad(local_name="PLAUD_NOTE", manufacturer_data=mfr)
        result = parser.parse(ad)
        assert result.raw_payload_hex == mfr.hex()

    def test_raw_payload_hex_empty_without_mfr(self):
        """raw_payload_hex is empty when no manufacturer data."""
        parser = PlaudParser()
        ad = _make_ad(local_name="PLAUD_NOTE")
        result = parser.parse(ad)
        assert result.raw_payload_hex == ""

    def test_company_id_in_metadata_note(self):
        """Company ID is extracted for PLAUD NOTE."""
        parser = PlaudParser()
        mfr = bytes.fromhex("590002780304565f0000098883163743897198850a0004f578ed1e0101")
        ad = _make_ad(local_name="PLAUD_NOTE", manufacturer_data=mfr)
        result = parser.parse(ad)
        assert result.metadata["company_id"] == 0x0059

    def test_company_id_in_metadata_notepin(self):
        """Company ID is extracted for PLAUD NotePin."""
        parser = PlaudParser()
        mfr = bytes.fromhex("5d000456d50000088800040122736261440a0004001828570101")
        ad = _make_ad(local_name="PLAUD NotePin", manufacturer_data=mfr)
        result = parser.parse(ad)
        assert result.metadata["company_id"] == 0x005D

    def test_model_extraction_underscore(self):
        """Model extracted from name with underscore separator."""
        parser = PlaudParser()
        ad = _make_ad(local_name="PLAUD_NOTE")
        result = parser.parse(ad)
        assert result.metadata["model"] == "NOTE"

    def test_model_extraction_space(self):
        """Model extracted from name with space separator."""
        parser = PlaudParser()
        ad = _make_ad(local_name="PLAUD NotePin")
        result = parser.parse(ad)
        assert result.metadata["model"] == "NotePin"
