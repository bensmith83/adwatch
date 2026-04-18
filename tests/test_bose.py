"""Tests for Bose audio device BLE advertisement plugin.

Source of truth for identifiers: apk-ble-hunting/reports/bose-bosemusic_passive.md.
"""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.bose import (
    BoseParser,
    BOSE_COMPANY_ID,
    BOSE_SERVICE_UUID_FEBE,
    BOSE_BMAP_SERVICE_UUID,
)


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
        service_uuid=[BOSE_SERVICE_UUID_FEBE, BOSE_BMAP_SERVICE_UUID],
        local_name_pattern=r"^Bose ",
        description="Bose audio device advertisements",
        version="1.1.0",
        core=False,
        registry=registry,
    )
    class TestParser(BoseParser):
        pass

    return registry


def _bose_mfr_data(company_id=None, payload=b"\x01\x02\x03"):
    if company_id is None:
        company_id = BOSE_COMPANY_ID
    return company_id.to_bytes(2, "little") + payload


class TestBoseIdentifiers:
    def test_company_id_is_0x009e(self):
        # Bose Corporation per Bluetooth SIG assigned numbers.
        assert BOSE_COMPANY_ID == 0x009E

    def test_primary_service_uuid_is_febe(self):
        assert BOSE_SERVICE_UUID_FEBE == "febe"

    def test_bmap_service_uuid(self):
        assert BOSE_BMAP_SERVICE_UUID.lower() == "d417c028-9818-4354-99d1-2ac09d074591"


class TestBoseMatching:
    def test_matches_bose_company_id(self):
        registry = _make_registry()
        ad = _make_ad(manufacturer_data=_bose_mfr_data())
        assert len(registry.match(ad)) == 1

    def test_matches_febe_service_uuid(self):
        registry = _make_registry()
        ad = _make_ad(service_uuids=["febe"])
        assert len(registry.match(ad)) == 1

    def test_matches_bmap_service_uuid(self):
        registry = _make_registry()
        ad = _make_ad(service_uuids=[BOSE_BMAP_SERVICE_UUID])
        assert len(registry.match(ad)) == 1

    def test_matches_febe_service_data(self):
        registry = _make_registry()
        ad = _make_ad(service_data={"febe": b"\xAA\xBB"})
        assert len(registry.match(ad)) == 1

    def test_matches_bose_local_name(self):
        registry = _make_registry()
        ad = _make_ad(local_name="Bose QC Ultra Headphones")
        assert len(registry.match(ad)) == 1

    def test_does_not_match_lenovo_company_id(self):
        # 0x0065 is NOT Bose — was a stale/wrong value in an earlier plugin.
        registry = _make_registry()
        ad = _make_ad(manufacturer_data=(0x0065).to_bytes(2, "little") + b"\x00")
        assert len(registry.match(ad)) == 0


class TestBoseParsing:
    def test_parses_with_company_id(self):
        parser = BoseParser()
        ad = _make_ad(manufacturer_data=_bose_mfr_data())
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "bose"
        assert result.beacon_type == "bose"
        assert result.device_class == "audio"

    def test_parses_with_only_service_uuid(self):
        # Passive report notes mfr data layout is runtime-constructed; scanners
        # must still be able to tag a Bose device from FEBE service UUID alone.
        parser = BoseParser()
        ad = _make_ad(service_uuids=["febe"])
        result = parser.parse(ad)
        assert result is not None
        assert result.device_class == "audio"

    def test_parses_with_only_bose_name(self):
        parser = BoseParser()
        ad = _make_ad(local_name="Bose SoundLink Flex")
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata.get("model_hint") == "SoundLink Flex"

    def test_model_hint_from_name_qc_ultra(self):
        parser = BoseParser()
        ad = _make_ad(local_name="Bose QC Ultra Headphones")
        result = parser.parse(ad)
        assert result.metadata.get("model_hint") == "QC Ultra Headphones"

    def test_returns_none_wrong_company_id_no_other_signal(self):
        parser = BoseParser()
        ad = _make_ad(manufacturer_data=(0x004C).to_bytes(2, "little") + b"\x01\x02")
        assert parser.parse(ad) is None

    def test_identity_hash_is_mac_based(self):
        mac = "11:22:33:44:55:66"
        parser = BoseParser()
        ad = _make_ad(manufacturer_data=_bose_mfr_data(), mac_address=mac)
        result = parser.parse(ad)
        expected = hashlib.sha256(mac.encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_payload_hex_in_metadata(self):
        parser = BoseParser()
        payload = b"\xAB\xCD\xEF"
        ad = _make_ad(manufacturer_data=_bose_mfr_data(payload=payload))
        result = parser.parse(ad)
        assert result.metadata["payload_hex"] == payload.hex()
        assert result.metadata["payload_length"] == 3

    def test_febe_service_data_extracted(self):
        parser = BoseParser()
        svc_payload = b"\x01\x02\x03\x04"
        ad = _make_ad(
            manufacturer_data=_bose_mfr_data(),
            service_data={"febe": svc_payload},
        )
        result = parser.parse(ad)
        assert result.metadata["service_payload_hex"] == svc_payload.hex()
        assert result.metadata["service_payload_length"] == 4

    def test_empty_service_data_not_added(self):
        parser = BoseParser()
        ad = _make_ad(
            manufacturer_data=_bose_mfr_data(),
            service_data={"febe": b""},
        )
        result = parser.parse(ad)
        assert "service_payload_hex" not in result.metadata

    def test_unrelated_service_data_ignored(self):
        parser = BoseParser()
        ad = _make_ad(
            manufacturer_data=_bose_mfr_data(),
            service_data={"fe78": b"\xAA"},  # Garmin
        )
        result = parser.parse(ad)
        assert "service_payload_hex" not in result.metadata
