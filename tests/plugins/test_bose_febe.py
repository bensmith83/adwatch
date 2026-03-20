"""Tests for Bose FEBE UUID support.

The Bose parser currently only matches service_uuid="fe78".
It needs to also match "febe" (which comes with company_id 0x0337, not 0x0065).
"""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser


BOSE_COMPANY_ID = 0x0065
FEBE_COMPANY_ID = 0x0337

# Existing Bose ad (company 0x0065, uuid fe78)
BOSE_MFR_DATA = bytes.fromhex("650001020304050607")

# FEBE ad (company 0x0337, uuid febe) — real sample
FEBE_MFR_DATA = bytes.fromhex("0337511009d262390f2ac02549")

BOSE_MAC = "AA:BB:CC:DD:EE:FF"


def make_raw(manufacturer_data=None, service_uuids=None, service_data=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-05T00:00:00+00:00",
        mac_address=BOSE_MAC,
        address_type="random",
        local_name=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        manufacturer_data=manufacturer_data,
        service_data=service_data,
        service_uuids=service_uuids or [],
        **defaults,
    )


class TestBoseFebeRegistryMatch:
    """The Bose parser must be matched by the registry for FEBE UUID ads."""

    def test_registry_matches_febe_uuid(self):
        """Registry should match Bose parser when service_uuid is 'febe'."""
        test_registry = ParserRegistry()

        # Import Bose parser and re-register with test registry
        from adwatch.plugins.bose import BoseParser
        # The fix: service_uuid should be ["fe78", "febe"] (a list)
        test_registry.register(
            name="bose",
            company_id=BOSE_COMPANY_ID,
            service_uuid=["fe78", "febe"],
            description="Bose audio device advertisements",
            version="1.0.0",
            core=False,
            instance=BoseParser(),
        )

        raw = make_raw(
            manufacturer_data=FEBE_MFR_DATA,
            service_uuids=["febe"],
        )
        matched = test_registry.match(raw)
        assert len(matched) == 1

    def test_registry_still_matches_fe78_uuid(self):
        """Registry should still match Bose parser for fe78 UUID."""
        test_registry = ParserRegistry()

        from adwatch.plugins.bose import BoseParser
        test_registry.register(
            name="bose",
            company_id=BOSE_COMPANY_ID,
            service_uuid=["fe78", "febe"],
            description="Bose audio device advertisements",
            version="1.0.0",
            core=False,
            instance=BoseParser(),
        )

        raw = make_raw(
            manufacturer_data=BOSE_MFR_DATA,
            service_uuids=["fe78"],
        )
        matched = test_registry.match(raw)
        assert len(matched) == 1


class TestBoseFebeParsing:
    """Bose parser must successfully parse FEBE ads (company 0x0337)."""

    @pytest.fixture
    def parser(self):
        from adwatch.plugins.bose import BoseParser
        return BoseParser()

    def test_febe_ad_not_rejected(self, parser):
        """FEBE ads have company_id 0x0337 — parser must NOT reject them."""
        raw = make_raw(
            manufacturer_data=FEBE_MFR_DATA,
            service_uuids=["febe"],
        )
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_febe_parser_name(self, parser):
        raw = make_raw(
            manufacturer_data=FEBE_MFR_DATA,
            service_uuids=["febe"],
        )
        result = parser.parse(raw)
        assert result.parser_name == "bose"

    def test_febe_device_class_audio(self, parser):
        raw = make_raw(
            manufacturer_data=FEBE_MFR_DATA,
            service_uuids=["febe"],
        )
        result = parser.parse(raw)
        assert result.device_class == "audio"

    def test_febe_identity_hash_format(self, parser):
        raw = make_raw(
            manufacturer_data=FEBE_MFR_DATA,
            service_uuids=["febe"],
        )
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        assert all(c in "0123456789abcdef" for c in result.identifier_hash)

    def test_febe_has_payload_hex(self, parser):
        raw = make_raw(
            manufacturer_data=FEBE_MFR_DATA,
            service_uuids=["febe"],
        )
        result = parser.parse(raw)
        assert len(result.raw_payload_hex) > 0


class TestBoseExistingBehavior:
    """Existing Bose behavior (company_id 0x0065) must still work."""

    @pytest.fixture
    def parser(self):
        from adwatch.plugins.bose import BoseParser
        return BoseParser()

    def test_standard_bose_still_parses(self, parser):
        raw = make_raw(
            manufacturer_data=BOSE_MFR_DATA,
            service_uuids=["fe78"],
        )
        result = parser.parse(raw)
        assert result is not None
        assert result.parser_name == "bose"

    def test_standard_bose_device_class(self, parser):
        raw = make_raw(
            manufacturer_data=BOSE_MFR_DATA,
            service_uuids=["fe78"],
        )
        result = parser.parse(raw)
        assert result.device_class == "audio"
