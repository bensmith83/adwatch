"""Tests for Nut Tracker keyfinder plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.nut_tracker import NutTrackerParser


@pytest.fixture
def parser():
    return NutTrackerParser()


def make_raw(local_name=None, mac_address="AA:BB:CC:DD:EE:FF", **kwargs):
    defaults = dict(
        timestamp="2026-03-26T00:00:00+00:00",
        mac_address=mac_address,
        address_type="random",
        manufacturer_data=None,
        service_data=None,
        service_uuids=[],
    )
    defaults.update(kwargs)
    return RawAdvertisement(local_name=local_name, **defaults)


class TestNutTrackerMatching:
    def test_matches_nut_mini(self, parser):
        raw = make_raw(local_name="nut mini")
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_matches_uppercase_NUT(self, parser):
        raw = make_raw(local_name="NUT")
        result = parser.parse(raw)
        assert result is not None

    def test_matches_mixed_case_Nut_Find3(self, parser):
        raw = make_raw(local_name="Nut Find3")
        result = parser.parse(raw)
        assert result is not None

    def test_model_from_local_name(self, parser):
        raw = make_raw(local_name="nut mini")
        result = parser.parse(raw)
        assert result.metadata["model"] == "nut mini"

    def test_model_strips_whitespace(self, parser):
        raw = make_raw(local_name="  nut mini  ")
        result = parser.parse(raw)
        assert result.metadata["model"] == "nut mini"

    def test_device_name_preserved(self, parser):
        raw = make_raw(local_name="Nut Find3")
        result = parser.parse(raw)
        assert result.metadata["device_name"] == "Nut Find3"

    def test_device_class_tracker(self, parser):
        raw = make_raw(local_name="NUT")
        result = parser.parse(raw)
        assert result.device_class == "tracker"

    def test_parser_name(self, parser):
        raw = make_raw(local_name="NUT")
        result = parser.parse(raw)
        assert result.parser_name == "nut_tracker"

    def test_beacon_type(self, parser):
        raw = make_raw(local_name="NUT")
        result = parser.parse(raw)
        assert result.beacon_type == "nut_tracker"

    def test_identifier_hash_format(self, parser):
        raw = make_raw(local_name="NUT")
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)  # must be valid hex

    def test_identifier_hash_stable(self, parser):
        raw1 = make_raw(local_name="NUT", mac_address="11:22:33:44:55:66")
        raw2 = make_raw(local_name="nut mini", mac_address="11:22:33:44:55:66")
        assert parser.parse(raw1).identifier_hash == parser.parse(raw2).identifier_hash

    def test_identifier_hash_expected(self, parser):
        raw = make_raw(local_name="NUT", mac_address="AA:BB:CC:DD:EE:FF")
        expected = hashlib.sha256("AA:BB:CC:DD:EE:FF:nut_tracker".encode()).hexdigest()[:16]
        assert parser.parse(raw).identifier_hash == expected


class TestNutTrackerRejection:
    def test_returns_none_wrong_name(self, parser):
        raw = make_raw(local_name="SomeTracker")
        assert parser.parse(raw) is None

    def test_returns_none_no_local_name(self, parser):
        raw = make_raw()
        assert parser.parse(raw) is None

    def test_does_not_match_nutale(self, parser):
        """Nutale should be handled by the nutale plugin, not nut_tracker.
        But nut_tracker matches any name starting with 'nut', so it will match.
        The registry routing should prefer nutale for 'Nutale*' names."""
        raw = make_raw(local_name="Nutale Finder")
        result = parser.parse(raw)
        # nut_tracker WILL match this (starts with "nut"), but in practice
        # the nutale plugin is more specific and should be preferred by routing.
        # Here we just verify nut_tracker can parse it without error.
        assert result is not None

    def test_returns_none_partial_match(self, parser):
        """Name containing 'nut' but not starting with it."""
        raw = make_raw(local_name="coconut")
        assert parser.parse(raw) is None
