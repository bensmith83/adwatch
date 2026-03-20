"""Tests for Philips Sonicare toothbrush plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.philips_sonicare import PhilipsSonicareParser


SONICARE_UUID = "477ea600-a260-11e4-ae37-0002a5d50001"

MAC = "AA:BB:CC:DD:EE:FF"


@pytest.fixture
def parser():
    return PhilipsSonicareParser()


def make_raw(local_name=None, service_uuids=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-05T00:00:00+00:00",
        mac_address=MAC,
        address_type="random",
        manufacturer_data=None,
        service_data=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        local_name=local_name,
        service_uuids=service_uuids or [],
        **defaults,
    )


class TestPhilipsSonicareParsing:
    def test_parse_with_name_returns_result(self, parser):
        raw = make_raw(local_name="Sonicare DiamondClean")
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parse_with_uuid_returns_result(self, parser):
        raw = make_raw(service_uuids=[SONICARE_UUID])
        result = parser.parse(raw)
        assert result is not None

    def test_parse_with_both(self, parser):
        raw = make_raw(local_name="Sonicare", service_uuids=[SONICARE_UUID])
        result = parser.parse(raw)
        assert result is not None

    def test_name_contains_sonicare(self, parser):
        """local_name_pattern is r'Sonicare' (not anchored), so substring match."""
        raw = make_raw(local_name="Philips Sonicare 9900")
        result = parser.parse(raw)
        assert result is not None

    def test_parser_name(self, parser):
        raw = make_raw(local_name="Sonicare")
        result = parser.parse(raw)
        assert result.parser_name == "philips_sonicare"

    def test_beacon_type(self, parser):
        raw = make_raw(local_name="Sonicare")
        result = parser.parse(raw)
        assert result.beacon_type == "philips_sonicare"

    def test_device_class_personal_care(self, parser):
        raw = make_raw(local_name="Sonicare")
        result = parser.parse(raw)
        assert result.device_class == "personal_care"

    def test_identity_hash(self, parser):
        """Identity = SHA256('{mac}:{local_name}')[:16] per protocol doc."""
        raw = make_raw(local_name="Sonicare DiamondClean")
        result = parser.parse(raw)
        expected = hashlib.sha256(f"{MAC}:Sonicare DiamondClean".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_format(self, parser):
        raw = make_raw(local_name="Sonicare")
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_metadata_device_name(self, parser):
        raw = make_raw(local_name="Sonicare DiamondClean")
        result = parser.parse(raw)
        assert result.metadata["device_name"] == "Sonicare DiamondClean"


class TestPhilipsSonicareRejection:
    def test_returns_none_no_match(self, parser):
        raw = make_raw(local_name="OralB SmartSeries")
        assert parser.parse(raw) is None

    def test_returns_none_no_data(self, parser):
        raw = make_raw()
        assert parser.parse(raw) is None
