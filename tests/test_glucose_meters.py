"""Tests for the BLE blood-glucose-meter local-name plugin.

Per apk-ble-hunting/reports/dario-health_passive.md: the Dario app drives
third-party meters through the Validic SDK, whose `bluetooth.json` matches
scanned devices by *device-name regex* after a 0x1808 (SIG Glucose Service)
scan filter. 0x1808 is vendor-agnostic, so this plugin keys on the distinctive
names only:

    NiproBGM        Nipro TRUE METRIX AIR
    Accu-Chek…      Roche Accu-Chek Aviva Connect
    meter+NNNNNNNN  Roche Accu-Chek Guide / Instant (8-digit serial in the clear)
    FORA MD         ForaCare 4272
"""

import hashlib

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.glucose_meters import (
    GLUCOSE_METER_NAME_PATTERN,
    GLUCOSE_SERVICE_UUID,
    GlucoseMeterParser,
)


@pytest.fixture
def parser():
    return GlucoseMeterParser()


def make_raw(**kwargs):
    defaults = dict(
        timestamp="2026-08-16T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="public",
        manufacturer_data=None,
        service_data=None,
        service_uuids=[],
        local_name=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(
        name="glucose_meters",
        local_name_pattern=GLUCOSE_METER_NAME_PATTERN,
        description="BLE blood glucose meters",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(GlucoseMeterParser):
        pass

    return _P


class TestMatching:
    @pytest.mark.parametrize("name", [
        "NiproBGM",
        "Accu-Chek Aviva",
        "meter+12345678",
        "FORA MD",
    ])
    def test_matches_known_names(self, name):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(make_raw(local_name=name))) == 1

    def test_does_not_register_on_generic_glucose_service(self):
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(make_raw(service_uuids=[GLUCOSE_SERVICE_UUID])) == []

    def test_does_not_match_unrelated_name(self):
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(make_raw(local_name="MyPhone")) == []


class TestRocheSerial:
    def test_guide_instant_serial_extracted(self, parser):
        result = parser.parse(make_raw(local_name="meter+40123456", service_uuids=["1808"]))
        assert result is not None
        assert result.metadata["vendor"] == "Roche"
        assert result.metadata["model"] == "Accu-Chek Guide / Instant"
        assert result.metadata["serial_number"] == "40123456"
        assert result.metadata["serial_in_advertisement"] is True

    def test_identity_hash_from_serial(self, parser):
        result = parser.parse(make_raw(local_name="meter+40123456"))
        assert result.identifier_hash == hashlib.sha256(
            b"accu_chek:40123456"
        ).hexdigest()[:16]

    def test_serial_identity_survives_mac_change(self, parser):
        a = parser.parse(make_raw(local_name="meter+40123456"))
        b = parser.parse(make_raw(local_name="meter+40123456", mac_address="11:22:33:44:55:66"))
        assert a.identifier_hash == b.identifier_hash

    def test_seven_digit_serial_is_not_a_match(self, parser):
        assert parser.parse(make_raw(local_name="meter+4012345")) is None


class TestOtherMeters:
    def test_nipro(self, parser):
        result = parser.parse(make_raw(local_name="NiproBGM"))
        assert result.metadata["vendor"] == "Nipro"
        assert result.metadata["model"] == "TRUE METRIX AIR"
        assert "serial_number" not in result.metadata

    def test_accu_chek_aviva_connect(self, parser):
        result = parser.parse(make_raw(local_name="Accu-Chek Aviva"))
        assert result.metadata["vendor"] == "Roche"
        assert result.metadata["model"] == "Accu-Chek Aviva Connect"

    def test_foracare(self, parser):
        result = parser.parse(make_raw(local_name="FORA MD"))
        assert result.metadata["vendor"] == "ForaCare"
        assert result.metadata["model"] == "FORA 4272"

    def test_common_fields(self, parser):
        result = parser.parse(make_raw(local_name="NiproBGM", service_uuids=["1808"]))
        assert result.parser_name == "glucose_meters"
        assert result.beacon_type == "glucose_meter"
        assert result.device_class == "medical"
        assert result.metadata["device_name"] == "NiproBGM"
        assert result.metadata["has_sig_glucose_service"] is True

    def test_glucose_service_flag_absent(self, parser):
        result = parser.parse(make_raw(local_name="NiproBGM"))
        assert "has_sig_glucose_service" not in result.metadata

    def test_identity_falls_back_to_mac(self, parser):
        result = parser.parse(make_raw(local_name="NiproBGM"))
        assert result.identifier_hash == hashlib.sha256(
            b"glucose_meter:Nipro:AA:BB:CC:DD:EE:FF"
        ).hexdigest()[:16]


class TestNegatives:
    def test_no_name_returns_none(self, parser):
        assert parser.parse(make_raw(service_uuids=["1808"])) is None

    def test_unrelated_name_returns_none(self, parser):
        assert parser.parse(make_raw(local_name="Accu-Weather")) is None

    def test_name_must_be_a_prefix(self, parser):
        assert parser.parse(make_raw(local_name="not a meter+12345678")) is None

    def test_storage_schema_is_none(self, parser):
        assert parser.storage_schema() is None


class TestOmronDoesNotDoubleClaim:
    """omron.py registers the vendor-agnostic 0x1808 UUID; it must not also
    claim a meter whose advertised name identifies another vendor."""

    def test_omron_yields_nothing_for_roche_meter(self):
        from adwatch.plugins.omron import OmronParser

        raw = make_raw(local_name="meter+40123456", service_uuids=["1808"])
        assert OmronParser().parse(raw) is None
