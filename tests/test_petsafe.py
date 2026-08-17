"""Tests for the PetSafe / Radio Systems Corp plugin.

Source: apk-ble-hunting/reports/net-petsafe-platform_passive.md — UUIDs were
recovered from base64 blobs inside libps-ble-provisioner-native-lib.so.
"""

import hashlib

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.petsafe import (
    PetSafeParser,
    PETSAFE_SERVICE_UUIDS,
    RADIO_SYSTEMS_COMPANY_ID,
    COLLAR_DATA_TRANSFER_UUID,
    COLLAR_TELEMETRY_UUID,
    SDT_SERVICE_UUID,
    RSC_SENTINEL_UUID,
)


def _make_ad(**kw):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "public",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _mfr(company_id, payload=b""):
    return company_id.to_bytes(2, "little") + payload


def _register(registry):
    @register_parser(
        name="petsafe",
        company_id=RADIO_SYSTEMS_COMPANY_ID,
        service_uuid=list(PETSAFE_SERVICE_UUIDS),
        description="PetSafe",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(PetSafeParser):
        pass

    return _P


class TestPetSafeMatching:
    @pytest.mark.parametrize("uuid", sorted(PETSAFE_SERVICE_UUIDS))
    def test_matches_each_service_uuid(self, uuid):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(service_uuids=[uuid]))) == 1

    def test_matches_radio_systems_company_id(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=_mfr(RADIO_SYSTEMS_COMPANY_ID, b"\x01\x02"))
        assert len(registry.match(ad)) == 1

    def test_company_id_is_little_endian_0x01fe(self):
        assert RADIO_SYSTEMS_COMPANY_ID == 0x01FE
        ad = _make_ad(manufacturer_data=bytes.fromhex("fe01aabb"))
        assert ad.company_id == RADIO_SYSTEMS_COMPANY_ID

    def test_no_match_unrelated(self):
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(_make_ad(manufacturer_data=_mfr(0x004C, b"\x00"))) == []
        assert registry.match(_make_ad(service_uuids=["180f"])) == []


class TestPetSafeFamilies:
    def test_collar_data_transfer(self):
        result = PetSafeParser().parse(_make_ad(service_uuids=[COLLAR_DATA_TRANSFER_UUID]))
        assert result is not None
        assert result.metadata["family"] == "collar"
        assert result.metadata["service_role"] == "collar_data_transfer"
        assert result.device_class == "pet_tracker"

    def test_collar_telemetry(self):
        result = PetSafeParser().parse(_make_ad(service_uuids=[COLLAR_TELEMETRY_UUID]))
        assert result.metadata["family"] == "collar"
        assert result.metadata["service_role"] == "collar_telemetry"

    def test_sdt_family(self):
        result = PetSafeParser().parse(_make_ad(service_uuids=[SDT_SERVICE_UUID]))
        assert result.metadata["family"] == "sdt"
        assert result.metadata["service_role"] == "sdt_commands"
        assert result.device_class == "access_control"

    def test_sentinel_family(self):
        result = PetSafeParser().parse(_make_ad(service_uuids=[RSC_SENTINEL_UUID]))
        assert result.metadata["family"] == "sentinel"
        assert result.metadata["rsc_signature"] is True

    def test_rsc_prefix_detected_on_unknown_suffix(self):
        # Bytes 0-3 of the UUID spell "RSC\0" -- the Radio Systems signature.
        # The registry can only match exact UUIDs, so an unknown-suffix RSC
        # UUID is reached via the company ID and identified inside parse().
        ad = _make_ad(
            manufacturer_data=_mfr(RADIO_SYSTEMS_COMPANY_ID),
            service_uuids=["52534300-1111-2222-3333-444455556666"],
        )
        result = PetSafeParser().parse(ad)
        assert result.metadata["rsc_signature"] is True
        assert result.metadata["family"] == "unknown"

    def test_company_id_only(self):
        ad = _make_ad(manufacturer_data=_mfr(RADIO_SYSTEMS_COMPANY_ID, b"\xaa\xbb"))
        result = PetSafeParser().parse(ad)
        assert result is not None
        assert result.metadata["family"] == "unknown"
        assert result.metadata["company_id_hex"] == "0x01FE"
        assert result.raw_payload_hex == "aabb"


class TestPetSafeParsing:
    def test_basics(self):
        result = PetSafeParser().parse(_make_ad(service_uuids=[COLLAR_TELEMETRY_UUID]))
        assert result.parser_name == "petsafe"
        assert result.beacon_type == "petsafe"
        assert result.metadata["vendor"] == "Radio Systems Corp (PetSafe)"

    def test_collar_uuid_mint_date_decoded(self):
        # a2efa8a6-74b0-11ed-... is a v1 UUID; its embedded timestamp dates
        # the collar generation.
        result = PetSafeParser().parse(_make_ad(service_uuids=[COLLAR_DATA_TRANSFER_UUID]))
        assert result.metadata["uuid_minted"] == "2022-12-05"

    def test_non_v1_uuid_has_no_mint_date(self):
        result = PetSafeParser().parse(_make_ad(service_uuids=[SDT_SERVICE_UUID]))
        assert "uuid_minted" not in result.metadata

    def test_device_name_recorded(self):
        result = PetSafeParser().parse(
            _make_ad(service_uuids=[SDT_SERVICE_UUID], local_name="SmartDoor")
        )
        assert result.metadata["device_name"] == "SmartDoor"

    def test_identity_hash_is_mac_based(self):
        result = PetSafeParser().parse(_make_ad(service_uuids=[SDT_SERVICE_UUID]))
        expected = hashlib.sha256(b"petsafe:AA:BB:CC:DD:EE:FF").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_returns_none_unrelated(self):
        assert PetSafeParser().parse(_make_ad(local_name="Collar")) is None
        assert PetSafeParser().parse(_make_ad(manufacturer_data=_mfr(0x004C))) is None
