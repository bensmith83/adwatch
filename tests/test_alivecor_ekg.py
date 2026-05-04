"""Tests for AliveCor KardiaMobile EKG BLE advertisement plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.alivecor_ekg import AliveCorEkgParser, ALIVECOR_SERVICE_UUID


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
        service_uuid=ALIVECOR_SERVICE_UUID,
        local_name_pattern=r"^EKG-",
        description="AliveCor KardiaMobile EKG advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(AliveCorEkgParser):
        pass

    return registry


class TestAliveCorEkgRegistry:
    def test_matches_local_name_pattern(self):
        """Matches on local_name 'EKG-99-23-4c' via name pattern."""
        registry = _make_registry()
        ad = _make_ad(local_name="EKG-99-23-4c")
        matches = registry.match(ad)
        assert len(matches) >= 1

    def test_matches_service_uuid(self):
        """Matches on service_uuid containing the AliveCor UUID."""
        registry = _make_registry()
        ad = _make_ad(
            service_uuids=["021a9004-0382-4aea-bff4-6b3f1c5adfb4"],
        )
        matches = registry.match(ad)
        assert len(matches) >= 1


class TestAliveCorEkgParser:
    def test_parser_name(self):
        """parser_name is 'alivecor_ekg'."""
        parser = AliveCorEkgParser()
        ad = _make_ad(local_name="EKG-99-23-4c")
        result = parser.parse(ad)
        assert result.parser_name == "alivecor_ekg"

    def test_beacon_type(self):
        """beacon_type is 'alivecor_ekg'."""
        parser = AliveCorEkgParser()
        ad = _make_ad(local_name="EKG-99-23-4c")
        result = parser.parse(ad)
        assert result.beacon_type == "alivecor_ekg"

    def test_device_class_medical(self):
        """device_class is 'medical'."""
        parser = AliveCorEkgParser()
        ad = _make_ad(local_name="EKG-99-23-4c")
        result = parser.parse(ad)
        assert result.device_class == "medical"

    def test_device_id_extraction(self):
        """'EKG-99-23-4c' -> metadata['device_id']='99-23-4c'."""
        parser = AliveCorEkgParser()
        ad = _make_ad(local_name="EKG-99-23-4c")
        result = parser.parse(ad)
        assert result.metadata["device_id"] == "99-23-4c"

    def test_local_name_in_metadata(self):
        """metadata['local_name'] preserves the raw local_name."""
        parser = AliveCorEkgParser()
        ad = _make_ad(local_name="EKG-99-23-4c")
        result = parser.parse(ad)
        assert result.metadata["local_name"] == "EKG-99-23-4c"

    def test_identity_hash_uses_device_id(self):
        """v1.1.0: identity prefers device_id (survives MAC rotation)."""
        mac = "11:22:33:44:55:66"
        parser = AliveCorEkgParser()
        ad = _make_ad(local_name="EKG-99-23-4c", mac_address=mac)
        result = parser.parse(ad)
        expected = hashlib.sha256(b"alivecor_ekg:99-23-4c").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_falls_back_to_mac(self):
        """No device_id => SHA256(mac:alivecor_ekg)[:16]."""
        mac = "11:22:33:44:55:66"
        parser = AliveCorEkgParser()
        ad = _make_ad(service_uuids=[ALIVECOR_SERVICE_UUID], mac_address=mac)
        result = parser.parse(ad)
        expected = hashlib.sha256(f"{mac}:alivecor_ekg".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_raw_payload_hex_empty_no_manufacturer_data(self):
        """raw_payload_hex is '' when no manufacturer_data (typical for this device)."""
        parser = AliveCorEkgParser()
        ad = _make_ad(local_name="EKG-99-23-4c")
        result = parser.parse(ad)
        assert result.raw_payload_hex == ""

    def test_raw_payload_hex_with_manufacturer_data(self):
        """raw_payload_hex contains hex if manufacturer_data is present."""
        parser = AliveCorEkgParser()
        mfr_data = b"\x01\x02\xDE\xAD\xBE\xEF"
        ad = _make_ad(local_name="EKG-99-23-4c", manufacturer_data=mfr_data)
        result = parser.parse(ad)
        assert result.raw_payload_hex == mfr_data.hex()

    def test_service_uuid_match_without_local_name(self):
        """Parses with service_uuid match even when local_name is None."""
        parser = AliveCorEkgParser()
        ad = _make_ad(
            service_uuids=["021a9004-0382-4aea-bff4-6b3f1c5adfb4"],
        )
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "alivecor_ekg"
        assert "device_id" not in result.metadata

    def test_local_name_match_without_service_uuid(self):
        """Parses with local_name match even without service_uuids."""
        parser = AliveCorEkgParser()
        ad = _make_ad(local_name="EKG-12-34-56")
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["device_id"] == "12-34-56"

    def test_returns_none_no_local_name_no_service_uuid(self):
        """Returns None when local_name is None and no matching service UUID."""
        parser = AliveCorEkgParser()
        ad = _make_ad()
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_non_matching_name_no_service_uuid(self):
        """Returns None for non-matching name and no matching service UUID."""
        parser = AliveCorEkgParser()
        ad = _make_ad(local_name="SomeDevice")
        result = parser.parse(ad)
        assert result is None

    def test_ekg_prefix_only_no_suffix(self):
        """'EKG-' alone (no suffix) -> device_id is empty string or not in metadata."""
        parser = AliveCorEkgParser()
        ad = _make_ad(local_name="EKG-")
        result = parser.parse(ad)
        assert result is not None
        # device_id should be "" or absent
        device_id = result.metadata.get("device_id")
        assert device_id == "" or device_id is None


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
