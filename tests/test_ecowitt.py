"""Tests for the Ecowitt WS View plugin.

Ground truth: apk-ble-hunting report ``ecowitt-wsview_passive.md``
(``com.ost.wsview``, Stage 4b).  Ecowitt BLE is provisioning-only: the console
advertises a Complete Local Name and, while in setup mode, the ``0xAAAA``
provisioning service UUID.  There is no manufacturer data, no service data and
no telemetry — every weather reading travels over WiFi.
"""

import hashlib

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.ecowitt import (
    EcowittParser,
    ECOWITT_NAME_PATTERN,
    PROVISIONING_UUID,
)


def _make_ad(**kwargs):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "public",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _registry():
    reg = ParserRegistry()

    @register_parser(
        name="ecowitt", local_name_pattern=ECOWITT_NAME_PATTERN,
        description="Ecowitt", version="1.0.0", core=False, registry=reg,
    )
    class _P(EcowittParser):
        pass

    return reg


class TestEcowittMatching:
    @pytest.mark.parametrize("name", [
        "WS1900",
        "WS1900AB12",
        "WS1950",
        "HP10",
        "HP1012CD",
        "AMBWeather-4F2A",
        "ambweather-4f2a",
    ])
    def test_matches_ecowitt_names(self, name):
        assert len(_registry().match(_make_ad(local_name=name))) == 1

    @pytest.mark.parametrize("name", [
        "WS",
        "WS20",
        "HP",
        "HP LaserJet",
        "MyWS1900",       # must anchor at the start
        "Weather Station",
    ])
    def test_ignores_other_names(self, name):
        assert _registry().match(_make_ad(local_name=name)) == []

    def test_provisioning_uuid_alone_does_not_match(self):
        """0xAAAA is an unassigned 16-bit UUID reused by many cheap modules."""
        ad = _make_ad(service_uuids=[PROVISIONING_UUID])
        assert _registry().match(ad) == []


class TestEcowittParse:
    def test_console_presence(self):
        result = EcowittParser().parse(_make_ad(local_name="WS1900AB12"))
        assert result is not None
        assert result.parser_name == "ecowitt"
        assert result.beacon_type == "ecowitt"
        assert result.device_class == "sensor"
        assert result.metadata["local_name"] == "WS1900AB12"
        assert result.metadata["model_family"] == "WS1900"
        assert result.metadata["telemetry"] is False

    @pytest.mark.parametrize("name,family", [
        ("WS1950XY", "WS1950"),
        ("WS1900AB", "WS1900"),
        ("HP1012CD", "HP10"),
        ("AMBWeather-4F2A", "AMBWeather"),
    ])
    def test_model_family(self, name, family):
        result = EcowittParser().parse(_make_ad(local_name=name))
        assert result.metadata["model_family"] == family

    def test_provisioning_mode_from_service_uuid(self):
        """Advertising 0xAAAA means the console is unprovisioned / in setup."""
        ad = _make_ad(local_name="WS1900", service_uuids=[PROVISIONING_UUID])
        result = EcowittParser().parse(ad)
        assert result.metadata["provisioning_mode"] is True

    def test_provisioning_mode_accepts_full_128bit_uuid(self):
        ad = _make_ad(
            local_name="WS1900",
            service_uuids=["0000aaaa-0000-1000-8000-00805f9b34fb"],
        )
        assert EcowittParser().parse(ad).metadata["provisioning_mode"] is True

    def test_provisioning_mode_false_without_uuid(self):
        result = EcowittParser().parse(_make_ad(local_name="WS1900"))
        assert result.metadata["provisioning_mode"] is False

    def test_identity_hash_uses_mac(self):
        """BK7231/OPL1000 modules use a static public MAC."""
        ad = _make_ad(local_name="WS1900", mac_address="11:22:33:44:55:66")
        assert EcowittParser().parse(ad).identifier_hash == hashlib.sha256(
            b"ecowitt:11:22:33:44:55:66"
        ).hexdigest()[:16]

    def test_manufacturer_data_is_not_expected(self):
        """Ecowitt adverts carry no AD-type-0xFF element; if one shows up we
        still match on the name but report nothing from it."""
        ad = _make_ad(local_name="WS1900", manufacturer_data=b"\x4c\x00\x02\x15")
        result = EcowittParser().parse(ad)
        assert result is not None
        assert result.raw_payload_hex == ""

    def test_unmatched_name_returns_none(self):
        assert EcowittParser().parse(_make_ad(local_name="HP LaserJet")) is None

    def test_no_name_returns_none(self):
        assert EcowittParser().parse(_make_ad()) is None
