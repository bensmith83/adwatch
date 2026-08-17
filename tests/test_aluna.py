"""Tests for the Aluna smart-spirometer plugin.

Per apk-ble-hunting/reports/aluna-app_passive.md.
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.aluna import (
    AlunaParser,
    ALUNA_SERVICE_UUID,
    ALUNA_COMPANY_ID,
)


def _make_ad(**kw):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "CC:78:AB:12:34:56",
        "address_type": "public",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(
        name="aluna",
        company_id=ALUNA_COMPANY_ID,
        service_uuid=ALUNA_SERVICE_UUID,
        description="Aluna",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(AlunaParser):
        pass

    return _P


class TestAlunaMatching:
    def test_matches_service_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(service_uuids=[ALUNA_SERVICE_UUID]))) == 1

    def test_matches_uppercase_service_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[ALUNA_SERVICE_UUID.upper()])
        assert len(registry.match(ad)) == 1

    def test_matches_company_id(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=bytes([0xE4, 0x06, 0x01, 0x02]))
        assert len(registry.match(ad)) == 1

    def test_unrelated_uuid_does_not_match(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=["0000180d-0000-1000-8000-00805f9b34fb"])
        assert registry.match(ad) == []


class TestAlunaParsing:
    def test_uuid_detection(self):
        result = AlunaParser().parse(_make_ad(service_uuids=[ALUNA_SERVICE_UUID]))
        assert result is not None
        assert result.metadata["match_source"] == "service_uuid"
        assert result.device_class == "medical"

    def test_company_id_detection(self):
        ad = _make_ad(manufacturer_data=bytes([0xE4, 0x06, 0x01, 0x02]))
        result = AlunaParser().parse(ad)
        assert result is not None
        assert result.metadata["match_source"] == "company_id"

    def test_uuid_wins_when_both_present(self):
        ad = _make_ad(
            service_uuids=[ALUNA_SERVICE_UUID],
            manufacturer_data=bytes([0xE4, 0x06, 0x01, 0x02]),
        )
        assert AlunaParser().parse(ad).metadata["match_source"] == "service_uuid"

    def test_payload_hex_recorded_but_not_decoded(self):
        """The app parses no manufacturer data — layout is unknown."""
        ad = _make_ad(
            service_uuids=[ALUNA_SERVICE_UUID],
            manufacturer_data=bytes([0xE4, 0x06, 0xDE, 0xAD]),
        )
        result = AlunaParser().parse(ad)
        assert result.metadata["payload_hex"] == "dead"
        assert "battery_percent" not in result.metadata

    def test_local_name_recorded(self):
        ad = _make_ad(service_uuids=[ALUNA_SERVICE_UUID], local_name="Aluna-01")
        assert AlunaParser().parse(ad).metadata["device_name"] == "Aluna-01"

    def test_name_alone_does_not_match(self):
        """The app configures no name filter; the name format is unknown."""
        assert AlunaParser().parse(_make_ad(local_name="Aluna")) is None

    def test_returns_none_for_unrelated(self):
        ad = _make_ad(manufacturer_data=bytes([0x4C, 0x00, 0x02, 0x15]))
        assert AlunaParser().parse(ad) is None


class TestAlunaIdentityAndBasics:
    def test_identity_from_mac(self):
        ad = _make_ad(service_uuids=[ALUNA_SERVICE_UUID])
        result = AlunaParser().parse(ad)
        expected = hashlib.sha256(
            f"aluna:{ad.mac_address}".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_basics(self):
        result = AlunaParser().parse(_make_ad(service_uuids=[ALUNA_SERVICE_UUID]))
        assert result.parser_name == "aluna"
        assert result.beacon_type == "aluna"
        assert result.metadata["vendor"] == "Aluna"
        assert result.metadata["product"] == "smart spirometer"

    def test_constants(self):
        assert ALUNA_COMPANY_ID == 0x06E4
        assert ALUNA_SERVICE_UUID == "aaf0d58c-8ddb-4beb-ad66-41ae54fcb3d1"
