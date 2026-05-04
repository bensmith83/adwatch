"""Tests for Oticon hearing-aid plugin."""

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.oticon import OticonParser, ASHA_SERVICE_UUID, DEMANT_COMPANY_ID


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


def _register(registry):
    @register_parser(
        name="oticon",
        company_id=DEMANT_COMPANY_ID,
        service_uuid=ASHA_SERVICE_UUID,
        local_name_pattern=r"^Oticon ",
        description="Oticon",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(OticonParser):
        pass
    return _P


class TestOticonMatching:
    def test_match_asha_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[ASHA_SERVICE_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_oticon_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="Oticon Real R")
        assert len(registry.match(ad)) == 1


class TestOticonParsing:
    def test_oticon_name_with_side(self):
        result = OticonParser().parse(_make_ad(local_name="Oticon Real R"))
        assert result.metadata["model"] == "Real"
        assert result.metadata["side"] == "R"
        assert result.metadata["vendor_attribution"] == "oticon"

    def test_oticon_name_left(self):
        result = OticonParser().parse(_make_ad(local_name="Oticon More L"))
        assert result.metadata["side"] == "L"

    def test_asha_only_uncertain_attribution(self):
        result = OticonParser().parse(_make_ad(service_uuids=[ASHA_SERVICE_UUID]))
        assert result.metadata["asha_compliant"] is True
        assert result.metadata["vendor_attribution"] == "uncertain"

    def test_asha_plus_oticon_name_confirms(self):
        result = OticonParser().parse(_make_ad(
            service_uuids=[ASHA_SERVICE_UUID],
            local_name="Oticon Play L",
        ))
        assert result.metadata["vendor_attribution"] == "oticon"
        assert result.metadata["asha_compliant"] is True

    def test_returns_none_unrelated(self):
        assert OticonParser().parse(_make_ad(local_name="Other")) is None

    def test_parse_basics(self):
        result = OticonParser().parse(_make_ad(local_name="Oticon Real R"))
        assert result.parser_name == "oticon"
        assert result.device_class == "hearing_aid"
