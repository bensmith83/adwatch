"""Tests for Wellue / Viatom / Vtrump plugin."""

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.wellue_viatom import (
    WellueViatomParser,
    WELLUE_PRIMARY_UUID, VTRUMP_IBEACON_UUID,
    WELLUE_SERVICE_UUIDS,
)


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
        name="wellue_viatom",
        service_uuid=WELLUE_SERVICE_UUIDS,
        local_name_pattern=(
            r"(?i)(FHR-666|DuoEK|Checkme|KidsO2|BabyO2|O2Ring|OxyU|OxyRing|"
            r"OxyFit|Oxylink|OxySmart|Oxyfit|LEPU-ER|LP ER|ER1|ER2|ER3|VBeat|"
            r"BP2|BP3|Bioland|Lescale|MY_SCALE|BBSM|BUZUD|Aura_BP|SI PO|Viatom|"
            r"PC-60|PC80B|AOJ-20A|AP-20|T31|PM10|POD-1|POD-2B)"
        ),
        description="Wellue",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(WellueViatomParser):
        pass
    return _P


class TestWellueMatching:
    def test_match_wellue_primary_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[WELLUE_PRIMARY_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_o2ring_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="O2Ring-1234")
        assert len(registry.match(ad)) == 1

    def test_match_checkme_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="Checkme Pod-WPS")
        assert len(registry.match(ad)) == 1


class TestWellueProductClass:
    def test_o2ring_pulse_oximeter(self):
        result = WellueViatomParser().parse(_make_ad(local_name="O2Ring SC"))
        assert result.metadata["product_class"] == "continuous_pulse_oximeter_ring"

    def test_checkme_vitals(self):
        result = WellueViatomParser().parse(_make_ad(local_name="Checkme EX"))
        assert result.metadata["product_class"] == "vitals_monitor"

    def test_kidso2_pediatric(self):
        result = WellueViatomParser().parse(_make_ad(local_name="KidsO2-12345"))
        assert result.metadata["product_class"] == "pediatric_pulse_oximeter"

    def test_fhr_pregnancy(self):
        result = WellueViatomParser().parse(_make_ad(local_name="FHR-666(BLE)"))
        assert result.metadata["product_class"] == "fetal_heart_rate_doppler"

    def test_bp2_blood_pressure(self):
        result = WellueViatomParser().parse(_make_ad(local_name="BP2-foo"))
        assert result.metadata["product_class"] == "blood_pressure_monitor"

    def test_er1_ecg(self):
        result = WellueViatomParser().parse(_make_ad(local_name="ER1-H"))
        assert result.metadata["product_class"] == "ecg_patch"


class TestWellueOuiAndIbeacon:
    def test_oui_match_4d57(self):
        ad = _make_ad(mac_address="AA:BB:CC:DD:4D:57")
        result = WellueViatomParser().parse(ad)
        assert result is not None
        assert result.metadata["wellue_oui_hit"] is True

    def test_vtrump_ibeacon_flag(self):
        result = WellueViatomParser().parse(_make_ad(service_uuids=[VTRUMP_IBEACON_UUID]))
        assert result.metadata["vtrump_ibeacon_mode"] is True


class TestWellueBasics:
    def test_returns_none_unrelated(self):
        assert WellueViatomParser().parse(_make_ad(local_name="Other")) is None

    def test_parse_basics(self):
        result = WellueViatomParser().parse(_make_ad(local_name="O2Ring"))
        assert result.parser_name == "wellue_viatom"
        assert result.device_class == "medical"
