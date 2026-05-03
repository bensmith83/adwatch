"""Tests for Anki / DDL Vector plugin."""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.anki_vector import AnkiVectorParser, VECTOR_SERVICE_UUID


def _make_ad(**kw):
    defaults = {"timestamp": "2025-01-01T00:00:00Z", "mac_address": "AA:BB:CC:DD:EE:FF",
                "address_type": "random", "manufacturer_data": None, "service_data": None}
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(name="anki_vector", service_uuid=VECTOR_SERVICE_UUID,
                     local_name_pattern=r"^Vector-[A-Z0-9]{4}$",
                     description="Anki Vector", version="1.0.0", core=False,
                     registry=registry)
    class _P(AnkiVectorParser):
        pass
    return _P


class TestAnkiVectorMatching:
    def test_match_by_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[VECTOR_SERVICE_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_by_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="Vector-E4X2")
        assert len(registry.match(ad)) == 1

    def test_no_match_unrelated_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="VectorWhatever")
        assert len(registry.match(ad)) == 0


class TestAnkiVectorParsing:
    def test_extracts_esn_suffix_from_name(self):
        ad = _make_ad(service_uuids=[VECTOR_SERVICE_UUID], local_name="Vector-E4X2")
        result = AnkiVectorParser().parse(ad)
        assert result is not None
        assert result.metadata["esn_suffix"] == "E4X2"
        assert result.metadata["pairing_mode"] is True

    def test_uuid_only_no_esn_no_pairing_state(self):
        ad = _make_ad(service_uuids=[VECTOR_SERVICE_UUID])
        result = AnkiVectorParser().parse(ad)
        assert result is not None
        assert "esn_suffix" not in result.metadata

    def test_identity_uses_esn_suffix(self):
        ad = _make_ad(service_uuids=[VECTOR_SERVICE_UUID], local_name="Vector-ABCD",
                      mac_address="11:22:33:44:55:66")
        result = AnkiVectorParser().parse(ad)
        expected = hashlib.sha256(b"anki_vector:ABCD").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_falls_back_to_mac_when_no_esn(self):
        ad = _make_ad(service_uuids=[VECTOR_SERVICE_UUID], mac_address="11:22:33:44:55:66")
        result = AnkiVectorParser().parse(ad)
        expected = hashlib.sha256(b"anki_vector:11:22:33:44:55:66").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_returns_none_when_unrelated(self):
        ad = _make_ad(local_name="Other Device")
        assert AnkiVectorParser().parse(ad) is None

    def test_basics(self):
        ad = _make_ad(service_uuids=[VECTOR_SERVICE_UUID], local_name="Vector-E4X2")
        result = AnkiVectorParser().parse(ad)
        assert result.parser_name == "anki_vector"
        assert result.beacon_type == "anki_vector"
        assert result.device_class == "robot_toy"
