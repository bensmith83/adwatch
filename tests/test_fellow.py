"""Tests for Fellow (Stagg/Corvo) kettle plugin."""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.fellow import (
    FellowParser,
    FELLOW_PRIMARY_UUID,
    FELLOW_AUX_UUID,
)


def _make_ad(**kw):
    defaults = {"timestamp": "2025-01-01T00:00:00Z", "mac_address": "AA:BB:CC:DD:EE:FF",
                "address_type": "random", "manufacturer_data": None, "service_data": None}
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(name="fellow",
                     service_uuid=[FELLOW_PRIMARY_UUID, FELLOW_AUX_UUID],
                     local_name_pattern=r"^(Stagg EKG Pro|Corvo EKG|Fellow EKG Pro)",
                     description="Fellow", version="1.0.0", core=False,
                     registry=registry)
    class _P(FellowParser):
        pass
    return _P


class TestFellowMatching:
    def test_match_primary_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[FELLOW_PRIMARY_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_aux_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[FELLOW_AUX_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_name_stagg(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="Stagg EKG Pro")
        assert len(registry.match(ad)) == 1

    def test_match_name_corvo(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="Corvo EKG")
        assert len(registry.match(ad)) == 1


class TestFellowParsing:
    def test_stagg_model(self):
        ad = _make_ad(local_name="Stagg EKG Pro", service_uuids=[FELLOW_PRIMARY_UUID])
        result = FellowParser().parse(ad)
        assert result is not None
        assert result.metadata["model"] == "Stagg EKG Pro"

    def test_corvo_model(self):
        ad = _make_ad(local_name="Corvo EKG")
        result = FellowParser().parse(ad)
        assert result.metadata["model"] == "Corvo EKG"

    def test_fellow_branded_model(self):
        ad = _make_ad(local_name="Fellow EKG Pro")
        result = FellowParser().parse(ad)
        assert result.metadata["model"] == "Fellow EKG Pro"

    def test_uuid_only_unknown_model(self):
        ad = _make_ad(service_uuids=[FELLOW_PRIMARY_UUID])
        result = FellowParser().parse(ad)
        assert result is not None
        assert result.metadata.get("model") in (None, "unknown")

    def test_mac_suffix_id_when_name_carries_suffix(self):
        ad = _make_ad(local_name="Stagg EKG Pro-A1B2")
        result = FellowParser().parse(ad)
        assert result.metadata.get("mac_suffix") == "A1B2"

    def test_aux_uuid_flags_aux_service(self):
        ad = _make_ad(service_uuids=[FELLOW_AUX_UUID])
        result = FellowParser().parse(ad)
        assert result.metadata["aux_service_seen"] is True

    def test_returns_none_unrelated(self):
        assert FellowParser().parse(_make_ad(local_name="Other")) is None

    def test_basics(self):
        result = FellowParser().parse(_make_ad(local_name="Stagg EKG Pro"))
        assert result.parser_name == "fellow"
        assert result.beacon_type == "fellow"
        assert result.device_class == "kettle"

    def test_identity_uses_mac_suffix_when_present(self):
        ad = _make_ad(local_name="Stagg EKG Pro-CAFE", mac_address="11:22:33:44:55:66")
        result = FellowParser().parse(ad)
        expected = hashlib.sha256(b"fellow:CAFE").hexdigest()[:16]
        assert result.identifier_hash == expected
