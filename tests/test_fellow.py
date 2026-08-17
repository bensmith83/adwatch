"""Tests for Fellow (Stagg/Corvo "EKG") kettle plugin.

v1.1.0 adds the ``EKG-<hex tail>`` setup-beacon path: the only such unit ever
observed (``EKG-99-23-4c``) advertises the Espressif Wi-Fi-provisioning UUID
and was misattributed to AliveCor for a long time (docs/protocols/fellow.md).
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.fellow import (
    FellowParser,
    FELLOW_PRIMARY_UUID,
    FELLOW_AUX_UUID,
    FELLOW_NAME_PATTERN,
)

ESPRESSIF_PROV_UUID = "021a9004-0382-4aea-bff4-6b3f1c5adfb4"


def _make_ad(**kw):
    defaults = {"timestamp": "2025-01-01T00:00:00Z", "mac_address": "AA:BB:CC:DD:EE:FF",
                "address_type": "random", "manufacturer_data": None, "service_data": None}
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(name="fellow",
                     service_uuid=[FELLOW_PRIMARY_UUID, FELLOW_AUX_UUID],
                     local_name_pattern=FELLOW_NAME_PATTERN,
                     description="Fellow", version="1.1.0", core=False,
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


class TestFellowEkgSetupBeacon:
    """EKG-<hex tail> names (setup / provisioning beacon) belong to Fellow."""

    def test_registry_routes_ekg_tail_name(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(local_name="EKG-99-23-4c"))) == 1

    def test_registry_does_not_route_bare_espressif_prov_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(_make_ad(service_uuids=[ESPRESSIF_PROV_UUID])) == []

    def test_corpus_record_parses_with_provisioning_flag(self):
        ad = _make_ad(local_name="EKG-99-23-4c", service_uuids=[ESPRESSIF_PROV_UUID])
        result = FellowParser().parse(ad)
        assert result is not None
        assert result.parser_name == "fellow"
        assert result.device_class == "kettle"
        assert result.metadata["device_id"] == "99-23-4c"
        assert result.metadata["provisioning_mode"] is True
        assert result.metadata["match_basis"] == "name_ekg_tail+espressif_prov_uuid"
        assert "model_hint" in result.metadata

    def test_ekg_tail_name_only(self):
        result = FellowParser().parse(_make_ad(local_name="EKG-AB-CD-EF"))
        assert result is not None
        assert result.metadata["device_id"] == "AB-CD-EF"
        assert "provisioning_mode" not in result.metadata
        assert result.metadata["match_basis"] == "name_ekg_tail"

    def test_ekg_tail_identity_is_mac_independent(self):
        a = FellowParser().parse(_make_ad(local_name="EKG-99-23-4c", mac_address="11:11:11:11:11:11"))
        b = FellowParser().parse(_make_ad(local_name="EKG-99-23-4c", mac_address="22:22:22:22:22:22"))
        assert a.identifier_hash == b.identifier_hash
        assert a.identifier_hash == hashlib.sha256(b"fellow:99-23-4c").hexdigest()[:16]

    def test_ekg_non_hex_tail_rejected(self):
        assert FellowParser().parse(_make_ad(local_name="EKG-monitor")) is None
        assert FellowParser().parse(_make_ad(local_name="EKG-")) is None

    def test_espressif_prov_uuid_alone_not_claimed(self):
        assert FellowParser().parse(_make_ad(service_uuids=[ESPRESSIF_PROV_UUID])) is None
        assert FellowParser().parse(_make_ad(local_name="PROV_1234", service_uuids=[ESPRESSIF_PROV_UUID])) is None

    def test_personal_name_with_fellow_uuid_rejected(self):
        ad = _make_ad(local_name="Ben's kettle", service_uuids=[FELLOW_PRIMARY_UUID])
        assert FellowParser().parse(ad) is None

    def test_kardia_not_claimed(self):
        ad = _make_ad(local_name="KardiaMobile_6L_ABC123",
                      service_uuids=["ac060001-328c-a28f-9846-5a8aa212661b"])
        assert FellowParser().parse(ad) is None

    def test_model_name_match_basis(self):
        result = FellowParser().parse(_make_ad(local_name="Stagg EKG Pro-A1B2", service_uuids=[FELLOW_PRIMARY_UUID]))
        assert result.metadata["match_basis"] == "name_model+primary_uuid"
