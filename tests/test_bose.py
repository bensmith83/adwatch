"""Tests for Bose audio device BLE advertisement plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.bose import BoseParser, BOSE_COMPANY_ID, BOSE_FEBE_COMPANY_ID, BOSE_SERVICE_UUID_FDF7


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
        name="bose",
        company_id=BOSE_COMPANY_ID,
        service_uuid=["fe78", "febe"],
        description="Bose audio device advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(BoseParser):
        pass

    return registry


def _bose_mfr_data(company_id=BOSE_COMPANY_ID, payload=b"\x01\x02\x03"):
    """Build manufacturer data: company_id (LE) + payload."""
    return company_id.to_bytes(2, "little") + payload


class TestBoseParser:
    def test_matches_company_id_0x0065(self):
        """Matches on Bose company_id 0x0065."""
        registry = _make_registry()
        ad = _make_ad(manufacturer_data=_bose_mfr_data())
        matches = registry.match(ad)
        assert len(matches) >= 1

    def test_matches_febe_company_id_0x3703(self):
        """Parses successfully with FEBE company_id 0x3703."""
        parser = BoseParser()
        ad = _make_ad(manufacturer_data=_bose_mfr_data(company_id=BOSE_FEBE_COMPANY_ID))
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "bose"

    def test_service_uuid_fe78_match(self):
        """Registry matches on service_uuid fe78."""
        registry = _make_registry()
        ad = _make_ad(
            manufacturer_data=_bose_mfr_data(),
            service_data={"fe78": b"\xAA\xBB"},
        )
        matches = registry.match(ad)
        assert len(matches) >= 1

    def test_service_uuid_febe_match(self):
        """Registry matches on service_uuid febe."""
        registry = _make_registry()
        ad = _make_ad(
            manufacturer_data=_bose_mfr_data(),
            service_data={"febe": b"\xCC\xDD"},
        )
        matches = registry.match(ad)
        assert len(matches) >= 1

    def test_device_class_is_audio(self):
        """device_class is always 'audio'."""
        parser = BoseParser()
        ad = _make_ad(manufacturer_data=_bose_mfr_data())
        result = parser.parse(ad)
        assert result.device_class == "audio"

    def test_beacon_type(self):
        """beacon_type is 'bose'."""
        parser = BoseParser()
        ad = _make_ad(manufacturer_data=_bose_mfr_data())
        result = parser.parse(ad)
        assert result.beacon_type == "bose"

    def test_parser_name(self):
        """parser_name is 'bose'."""
        parser = BoseParser()
        ad = _make_ad(manufacturer_data=_bose_mfr_data())
        result = parser.parse(ad)
        assert result.parser_name == "bose"

    def test_identity_hash_format(self):
        """Identity hash is SHA256(mac_address)[:16]."""
        mac = "11:22:33:44:55:66"
        parser = BoseParser()
        ad = _make_ad(manufacturer_data=_bose_mfr_data(), mac_address=mac)
        result = parser.parse(ad)
        expected = hashlib.sha256(mac.encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_payload_hex_in_metadata(self):
        """payload_hex contains hex of manufacturer payload (without company_id)."""
        parser = BoseParser()
        payload = b"\xAB\xCD\xEF"
        ad = _make_ad(manufacturer_data=_bose_mfr_data(payload=payload))
        result = parser.parse(ad)
        assert result.metadata["payload_hex"] == payload.hex()

    def test_payload_length_in_metadata(self):
        """payload_length is length of payload bytes."""
        parser = BoseParser()
        payload = b"\x01\x02\x03\x04\x05"
        ad = _make_ad(manufacturer_data=_bose_mfr_data(payload=payload))
        result = parser.parse(ad)
        assert result.metadata["payload_length"] == 5

    def test_raw_payload_hex(self):
        """raw_payload_hex contains payload (without company_id) as hex."""
        parser = BoseParser()
        payload = b"\xDE\xAD\xBE\xEF"
        ad = _make_ad(manufacturer_data=_bose_mfr_data(payload=payload))
        result = parser.parse(ad)
        assert result.raw_payload_hex == payload.hex()

    def test_service_data_fdf7_extracted(self):
        """Service data for fdf7 UUID is extracted into metadata."""
        parser = BoseParser()
        svc_payload = b"\x01\x02\x03\x04"
        ad = _make_ad(
            manufacturer_data=_bose_mfr_data(),
            service_data={"fdf7": svc_payload},
        )
        result = parser.parse(ad)
        assert result.metadata["service_payload_hex"] == svc_payload.hex()
        assert result.metadata["service_payload_length"] == 4

    def test_service_data_fdf7_empty_not_added(self):
        """Empty fdf7 service data does not add service fields."""
        parser = BoseParser()
        ad = _make_ad(
            manufacturer_data=_bose_mfr_data(),
            service_data={"fdf7": b""},
        )
        result = parser.parse(ad)
        assert "service_payload_hex" not in result.metadata

    def test_no_service_data_no_service_fields(self):
        """Without service_data, no service fields in metadata."""
        parser = BoseParser()
        ad = _make_ad(manufacturer_data=_bose_mfr_data())
        result = parser.parse(ad)
        assert "service_payload_hex" not in result.metadata
        assert "service_payload_length" not in result.metadata

    def test_other_service_uuid_ignored(self):
        """Service data for non-fdf7 UUIDs doesn't add service fields."""
        parser = BoseParser()
        ad = _make_ad(
            manufacturer_data=_bose_mfr_data(),
            service_data={"fe78": b"\xAA\xBB"},
        )
        result = parser.parse(ad)
        assert "service_payload_hex" not in result.metadata

    def test_returns_none_wrong_company_id(self):
        """Returns None when company_id is not Bose or FEBE."""
        parser = BoseParser()
        # Apple company_id 0x004C
        data = (0x004C).to_bytes(2, "little") + b"\x01\x02\x03"
        ad = _make_ad(manufacturer_data=data)
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_short_data(self):
        """Returns None when manufacturer_data is less than 2 bytes."""
        parser = BoseParser()
        ad = _make_ad(manufacturer_data=b"\x65")
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_no_manufacturer_data(self):
        """Returns None when manufacturer_data is None."""
        parser = BoseParser()
        ad = _make_ad()
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_no_payload_after_company_id(self):
        """Returns None when manufacturer_data is exactly 2 bytes (company_id only)."""
        parser = BoseParser()
        ad = _make_ad(manufacturer_data=BOSE_COMPANY_ID.to_bytes(2, "little"))
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_febe_company_id_no_payload(self):
        """Returns None for FEBE company_id with no payload."""
        parser = BoseParser()
        ad = _make_ad(manufacturer_data=BOSE_FEBE_COMPANY_ID.to_bytes(2, "little"))
        result = parser.parse(ad)
        assert result is None

    def test_with_service_data_and_febe_company_id(self):
        """Full parse with FEBE company_id and fdf7 service data."""
        parser = BoseParser()
        payload = b"\x10\x20\x30"
        svc_payload = b"\xAA\xBB"
        ad = _make_ad(
            manufacturer_data=_bose_mfr_data(company_id=BOSE_FEBE_COMPANY_ID, payload=payload),
            service_data={"fdf7": svc_payload},
        )
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["payload_hex"] == payload.hex()
        assert result.metadata["service_payload_hex"] == svc_payload.hex()
        assert result.device_class == "audio"
