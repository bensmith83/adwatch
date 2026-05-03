"""Tests for BMW Find Mate (Bury tracker tag) plugin."""

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.bmw_bury_findmate import BmwBuryFindMateParser


def _make_ad(**kw):
    defaults = {"timestamp": "2025-01-01T00:00:00Z", "mac_address": "AA:BB:CC:DD:EE:FF",
                "address_type": "random", "manufacturer_data": None, "service_data": None}
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(name="bmw_bury_findmate", local_name_pattern=r"^BMW (FMT|FM1)$",
                     description="BMW", version="1.0.0", core=False, registry=registry)
    class _P(BmwBuryFindMateParser):
        pass
    return _P


class TestBmwBuryFindMate:
    def test_match_fmt_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="BMW FMT")
        assert len(registry.match(ad)) == 1

    def test_match_fm1_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="BMW FM1")
        assert len(registry.match(ad)) == 1

    def test_fmt_unregistered_state(self):
        result = BmwBuryFindMateParser().parse(_make_ad(local_name="BMW FMT"))
        assert result.metadata["state"] == "unregistered"
        assert result.metadata["state_label"] == "factory_fresh"

    def test_fm1_registered_state(self):
        result = BmwBuryFindMateParser().parse(_make_ad(local_name="BMW FM1"))
        assert result.metadata["state"] == "registered"

    def test_returns_none_unrelated(self):
        assert BmwBuryFindMateParser().parse(_make_ad(local_name="BMW FM2")) is None
        assert BmwBuryFindMateParser().parse(_make_ad(local_name="Other")) is None

    def test_parse_basics(self):
        result = BmwBuryFindMateParser().parse(_make_ad(local_name="BMW FMT"))
        assert result.parser_name == "bmw_bury_findmate"
        assert result.device_class == "tracker"
