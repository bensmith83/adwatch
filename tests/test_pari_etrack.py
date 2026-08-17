"""Tests for the PARI eTrack Controller nebulizer plugin.

Name encoding per apk-ble-hunting/reports/pari-onecf-paridev_passive.md.
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.pari_etrack import PariEtrackParser, PARI_NAME_PATTERN


def _make_ad(**kw):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "E8:99:AA:BB:CC:DD",
        "address_type": "public",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(
        name="pari_etrack",
        local_name_pattern=PARI_NAME_PATTERN,
        description="PARI eTrack",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(PariEtrackParser):
        pass

    return _P


class TestPariEtrackMatching:
    def test_matches_pari_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="PARI_A1B2C3D4E5_XY12")
        assert len(registry.match(ad)) == 1

    def test_bare_pari_prefix_does_not_match(self):
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(_make_ad(local_name="PARI_boiler")) == []

    def test_wrong_serial_length_does_not_match(self):
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(_make_ad(local_name="PARI_A1B2C3_XY12")) == []

    def test_wrong_suffix_length_does_not_match(self):
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(_make_ad(local_name="PARI_A1B2C3D4E5_XY1")) == []

    def test_unrelated_name_does_not_match(self):
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(_make_ad(local_name="eFlow")) == []


class TestPariEtrackDecode:
    def test_extracts_serial_and_model_code(self):
        result = PariEtrackParser().parse(_make_ad(local_name="PARI_A1B2C3D4E5_XY12"))
        assert result is not None
        assert result.metadata["serial"] == "A1B2C3D4E5"
        assert result.metadata["model_code"] == "XY12"
        assert result.metadata["device_name"] == "PARI_A1B2C3D4E5_XY12"

    def test_numeric_serial(self):
        result = PariEtrackParser().parse(_make_ad(local_name="PARI_0123456789_0001"))
        assert result.metadata["serial"] == "0123456789"
        assert result.metadata["model_code"] == "0001"

    def test_rejects_lowercase_prefix(self):
        assert PariEtrackParser().parse(_make_ad(local_name="pari_A1B2C3D4E5_XY12")) is None

    def test_rejects_extra_trailing_text(self):
        assert PariEtrackParser().parse(
            _make_ad(local_name="PARI_A1B2C3D4E5_XY12_extra")
        ) is None

    def test_rejects_missing_name(self):
        assert PariEtrackParser().parse(_make_ad()) is None

    def test_manufacturer_data_ignored(self):
        """eTrack advertises no app-relevant manufacturer data."""
        ad = _make_ad(
            local_name="PARI_A1B2C3D4E5_XY12",
            manufacturer_data=bytes([0x4C, 0x00, 0x01, 0x02]),
        )
        result = PariEtrackParser().parse(ad)
        assert result is not None
        assert result.metadata["serial"] == "A1B2C3D4E5"


class TestPariEtrackIdentityAndBasics:
    def test_identity_from_serial(self):
        result = PariEtrackParser().parse(_make_ad(local_name="PARI_A1B2C3D4E5_XY12"))
        expected = hashlib.sha256(b"pari_etrack:A1B2C3D4E5").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_stable_across_mac(self):
        a = _make_ad(local_name="PARI_A1B2C3D4E5_XY12", mac_address="AA:BB:CC:DD:EE:FF")
        b = _make_ad(local_name="PARI_A1B2C3D4E5_XY12", mac_address="11:22:33:44:55:66")
        assert PariEtrackParser().parse(a).identifier_hash == \
            PariEtrackParser().parse(b).identifier_hash

    def test_different_serials_differ(self):
        a = _make_ad(local_name="PARI_A1B2C3D4E5_XY12")
        b = _make_ad(local_name="PARI_Z9Y8X7W6V5_XY12")
        assert PariEtrackParser().parse(a).identifier_hash != \
            PariEtrackParser().parse(b).identifier_hash

    def test_basics(self):
        result = PariEtrackParser().parse(_make_ad(local_name="PARI_A1B2C3D4E5_XY12"))
        assert result.parser_name == "pari_etrack"
        assert result.beacon_type == "pari_etrack"
        assert result.device_class == "medical"
        assert result.metadata["vendor"] == "PARI"
        assert result.metadata["product"] == "eTrack Controller"
