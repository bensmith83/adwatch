"""Tests for Bose FEBE service-UUID matching.

The earlier version of this file asserted a company ID of 0x3703 against a
supposedly-Bose capture. Static analysis of the Bose Music APK
(apk-ble-hunting/reports/bose-bosemusic_passive.md) establishes that Bose uses
SIG company ID 0x009E (158) and SIG service UUID 0xFEBE. The real load-bearing
behavior is that the parser tags an ad as Bose when the FEBE service UUID is
present, regardless of whatever company ID the device advertises. Those tests
are preserved here.
"""

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry

from adwatch.plugins.bose import (
    BoseParser,
    BOSE_COMPANY_ID,
    BOSE_SERVICE_UUID_FEBE,
    BOSE_BMAP_SERVICE_UUID,
)


# Sample captured in the wild: starts with company ID bytes (whatever the
# device chose) and carries the FEBE service UUID separately. The parser must
# tag it as Bose via the UUID, not via the company ID prefix.
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
    def test_registry_matches_febe_uuid(self):
        registry = ParserRegistry()
        registry.register(
            name="bose",
            company_id=BOSE_COMPANY_ID,
            service_uuid=[BOSE_SERVICE_UUID_FEBE, BOSE_BMAP_SERVICE_UUID],
            description="Bose audio device advertisements",
            version="1.1.0",
            core=False,
            instance=BoseParser(),
        )

        raw = make_raw(
            manufacturer_data=FEBE_MFR_DATA,
            service_uuids=[BOSE_SERVICE_UUID_FEBE],
        )
        assert len(registry.match(raw)) == 1

    def test_registry_matches_bmap_uuid(self):
        registry = ParserRegistry()
        registry.register(
            name="bose",
            company_id=BOSE_COMPANY_ID,
            service_uuid=[BOSE_SERVICE_UUID_FEBE, BOSE_BMAP_SERVICE_UUID],
            description="Bose audio device advertisements",
            version="1.1.0",
            core=False,
            instance=BoseParser(),
        )

        raw = make_raw(service_uuids=[BOSE_BMAP_SERVICE_UUID])
        assert len(registry.match(raw)) == 1


class TestBoseFebeParsing:
    @pytest.fixture
    def parser(self):
        return BoseParser()

    def test_febe_ad_parses(self, parser):
        raw = make_raw(
            manufacturer_data=FEBE_MFR_DATA,
            service_uuids=[BOSE_SERVICE_UUID_FEBE],
        )
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)
        assert result.parser_name == "bose"
        assert result.device_class == "audio"

    def test_identity_hash_format(self, parser):
        raw = make_raw(
            manufacturer_data=FEBE_MFR_DATA,
            service_uuids=[BOSE_SERVICE_UUID_FEBE],
        )
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        assert all(c in "0123456789abcdef" for c in result.identifier_hash)


class TestBoseStandardCompanyId:
    @pytest.fixture
    def parser(self):
        return BoseParser()

    def test_standard_bose_parses(self, parser):
        raw = make_raw(
            manufacturer_data=BOSE_COMPANY_ID.to_bytes(2, "little") + bytes.fromhex("0102030405"),
        )
        result = parser.parse(raw)
        assert result is not None
        assert result.parser_name == "bose"
        assert result.device_class == "audio"
