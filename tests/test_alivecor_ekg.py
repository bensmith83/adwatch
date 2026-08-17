"""Tests for AliveCor Kardia ECG BLE advertisement plugin (v1.2.0, Kardia-only).

History: v1.0.0/v1.1.0 also matched the ``EKG-`` local-name prefix and the
``021a9004-…`` service UUID. Both were a misattribution — that UUID is the
Espressif Wi-Fi-provisioning service and the only unit ever observed with an
``EKG-`` name is a Fellow "EKG" smart kettle (see ``fellow.py`` /
docs/protocols/fellow.md). Those signals must now be REJECTED here.
"""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.alivecor_ekg import (
    AliveCorEkgParser,
    KARDIA_6L_UUID,
    KARDIACARD_UUID,
)

ESPRESSIF_PROV_UUID = "021a9004-0382-4aea-bff4-6b3f1c5adfb4"


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


def _make_registry():
    registry = ParserRegistry()

    @register_parser(
        name="alivecor_ekg",
        service_uuid=[KARDIA_6L_UUID, KARDIACARD_UUID],
        local_name_pattern=r"^Kardia",
        description="AliveCor Kardia ECG advertisements",
        version="1.2.0",
        core=False,
        registry=registry,
    )
    class TestParser(AliveCorEkgParser):
        pass

    return registry


class TestAliveCorEkgRegistry:
    def test_matches_kardia_local_name_pattern(self):
        """Matches on a Kardia local_name via name pattern."""
        registry = _make_registry()
        ad = _make_ad(local_name="KardiaMobile_6L_ABC123")
        assert len(registry.match(ad)) >= 1

    def test_matches_kardia_service_uuids(self):
        """Matches on either Kardia service UUID."""
        registry = _make_registry()
        assert len(registry.match(_make_ad(service_uuids=[KARDIA_6L_UUID]))) >= 1
        assert len(registry.match(_make_ad(service_uuids=[KARDIACARD_UUID]))) >= 1

    def test_does_not_match_ekg_name_or_espressif_uuid(self):
        """The retracted v1 keys (EKG- name, Espressif prov UUID) no longer route here."""
        registry = _make_registry()
        assert registry.match(_make_ad(local_name="EKG-99-23-4c")) == []
        assert registry.match(_make_ad(service_uuids=[ESPRESSIF_PROV_UUID])) == []


class TestAliveCorEkgParser:
    def test_parser_name_and_beacon_type(self):
        parser = AliveCorEkgParser()
        result = parser.parse(_make_ad(local_name="KardiaMobile_6L_ABC123"))
        assert result.parser_name == "alivecor_ekg"
        assert result.beacon_type == "alivecor_ekg"

    def test_device_class_medical(self):
        parser = AliveCorEkgParser()
        result = parser.parse(_make_ad(local_name="KardiaCard_DEF456"))
        assert result.device_class == "medical"

    def test_local_name_in_metadata(self):
        parser = AliveCorEkgParser()
        result = parser.parse(_make_ad(local_name="KardiaCard_DEF456"))
        assert result.metadata["local_name"] == "KardiaCard_DEF456"

    def test_identity_hash_falls_back_to_mac_for_uuid_only(self):
        """No device_id => SHA256(mac:alivecor_ekg)[:16]."""
        mac = "11:22:33:44:55:66"
        parser = AliveCorEkgParser()
        result = parser.parse(_make_ad(service_uuids=[KARDIA_6L_UUID], mac_address=mac))
        expected = hashlib.sha256(f"{mac}:alivecor_ekg".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_raw_payload_hex_empty_no_manufacturer_data(self):
        parser = AliveCorEkgParser()
        result = parser.parse(_make_ad(local_name="KardiaMobile_6L_ABC123"))
        assert result.raw_payload_hex == ""

    def test_raw_payload_hex_with_manufacturer_data(self):
        parser = AliveCorEkgParser()
        mfr_data = b"\x01\x02\xDE\xAD\xBE\xEF"
        result = parser.parse(_make_ad(local_name="KardiaMobile_6L_ABC123", manufacturer_data=mfr_data))
        assert result.raw_payload_hex == mfr_data.hex()

    def test_uuid_match_without_local_name(self):
        parser = AliveCorEkgParser()
        result = parser.parse(_make_ad(service_uuids=[KARDIACARD_UUID]))
        assert result is not None
        assert "device_id" not in result.metadata

    def test_returns_none_no_local_name_no_service_uuid(self):
        assert AliveCorEkgParser().parse(_make_ad()) is None

    def test_returns_none_non_matching_name_no_service_uuid(self):
        assert AliveCorEkgParser().parse(_make_ad(local_name="SomeDevice")) is None

    def test_returns_none_for_personal_name_even_with_kardia_uuid(self):
        """A present non-Kardia name is never claimed (name-gate safety)."""
        ad = _make_ad(local_name="Ben's ECG", service_uuids=[KARDIA_6L_UUID])
        assert AliveCorEkgParser().parse(ad) is None


class TestAliveCorRetractedEkgPath:
    """The EKG-<hex tail> family is a Fellow kettle, not AliveCor — must be rejected."""

    def test_ekg_name_rejected(self):
        assert AliveCorEkgParser().parse(_make_ad(local_name="EKG-99-23-4c")) is None
        assert AliveCorEkgParser().parse(_make_ad(local_name="EKG-")) is None

    def test_ekg_name_with_espressif_prov_uuid_rejected(self):
        ad = _make_ad(local_name="EKG-99-23-4c", service_uuids=[ESPRESSIF_PROV_UUID])
        assert AliveCorEkgParser().parse(ad) is None

    def test_espressif_prov_uuid_alone_rejected(self):
        assert AliveCorEkgParser().parse(_make_ad(service_uuids=[ESPRESSIF_PROV_UUID])) is None


class TestAliveCorKardiaModern:
    """v1.1.0: KardiaMobile 6L + KardiaCard support."""

    def test_kardia_6l_uuid(self):
        from adwatch.plugins.alivecor_ekg import KARDIA_6L_UUID
        parser = AliveCorEkgParser()
        ad = _make_ad(service_uuids=[KARDIA_6L_UUID])
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["product_family"] == "KardiaMobile 6L"

    def test_kardia_card_uuid(self):
        from adwatch.plugins.alivecor_ekg import KARDIACARD_UUID
        parser = AliveCorEkgParser()
        ad = _make_ad(service_uuids=[KARDIACARD_UUID])
        result = parser.parse(ad)
        assert result.metadata["product_family"] == "KardiaCard"

    def test_kardiamobile_6l_name_with_serial(self):
        parser = AliveCorEkgParser()
        ad = _make_ad(local_name="KardiaMobile_6L_ABC123")
        result = parser.parse(ad)
        assert result.metadata["product_family"] == "KardiaMobile 6L"
        assert result.metadata["device_id"] == "ABC123"

    def test_kardiacard_name_with_serial(self):
        parser = AliveCorEkgParser()
        ad = _make_ad(local_name="KardiaCard_DEF456")
        result = parser.parse(ad)
        assert result.metadata["product_family"] == "KardiaCard"
        assert result.metadata["device_id"] == "DEF456"

    def test_identity_uses_kardia_serial(self):
        parser = AliveCorEkgParser()
        ad = _make_ad(local_name="KardiaMobile_6L_ABC123",
                      mac_address="11:22:33:44:55:66")
        result = parser.parse(ad)
        expected = hashlib.sha256(b"alivecor_ekg:ABC123").hexdigest()[:16]
        assert result.identifier_hash == expected
