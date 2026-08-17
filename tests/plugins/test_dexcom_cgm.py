"""Tests for Dexcom CGM plugin.

Identifiers per apk-ble-hunting/reports/dexcom-g6_passive.md and
reports/dexcom-g7_passive.md. The earlier test file pinned a UUID that
wasn't actually Dexcom's; the constants are now the SIG-registered FEBC
(G6) and the community-documented G7 UUID.
"""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.dexcom_cgm import (
    DexcomCgmParser,
    DEXCOM_G6_SERVICE_UUID,
    DEXCOM_G7_SERVICE_UUID,
)


@pytest.fixture
def parser():
    return DexcomCgmParser()


def make_raw(service_uuids=None, local_name=None, **kwargs):
    defaults = dict(
        timestamp="2026-04-09T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        manufacturer_data=None,
        service_data=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        service_uuids=service_uuids or [],
        local_name=local_name,
        **defaults,
    )


DEVICE_INFO_UUID = "180a"


class TestDexcomConstants:
    def test_g6_uuid_is_febc(self):
        assert DEXCOM_G6_SERVICE_UUID == "febc"

    def test_g7_uuid(self):
        assert DEXCOM_G7_SERVICE_UUID == "f8083532-849e-531c-c594-30f1f86a4ea5"


class TestDexcomParsing:
    def test_parse_by_g6_service_uuid(self, parser):
        raw = make_raw(service_uuids=[DEVICE_INFO_UUID, DEXCOM_G6_SERVICE_UUID])
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["model"] == "G6"

    def test_parse_by_g7_service_uuid(self, parser):
        raw = make_raw(service_uuids=[DEXCOM_G7_SERVICE_UUID])
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["model"] == "G7"

    def test_parse_by_g6_name_format(self, parser):
        raw = make_raw(local_name="Dexcom8X")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["model"] == "G6"
        assert result.metadata["transmitter_serial_tail"] == "8X"

    def test_parse_by_g7_name_prefix(self, parser):
        raw = make_raw(local_name="DXCMXYZ123")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["model"] == "G7"

    def test_parse_result_fields(self, parser):
        raw = make_raw(service_uuids=[DEXCOM_G6_SERVICE_UUID])
        result = parser.parse(raw)
        assert result.parser_name == "dexcom_cgm"
        assert result.beacon_type == "dexcom_cgm"
        assert result.device_class == "medical"

    def test_identity_hash_uses_serial_tail_when_available(self, parser):
        raw = make_raw(local_name="Dexcom8X", mac_address="11:22:33:44:55:66")
        result = parser.parse(raw)
        expected = hashlib.sha256("dexcom_g6:8X".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_fallback(self, parser):
        raw = make_raw(
            service_uuids=[DEXCOM_G7_SERVICE_UUID], mac_address="11:22:33:44:55:66"
        )
        result = parser.parse(raw)
        expected = hashlib.sha256("11:22:33:44:55:66".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_metadata_device_name(self, parser):
        raw = make_raw(service_uuids=[DEXCOM_G6_SERVICE_UUID], local_name="Dexcom8X")
        result = parser.parse(raw)
        assert result.metadata["device_name"] == "Dexcom8X"

    def test_has_device_info_flag(self, parser):
        raw = make_raw(service_uuids=[DEVICE_INFO_UUID, DEXCOM_G6_SERVICE_UUID])
        result = parser.parse(raw)
        assert result.metadata.get("has_device_info") is True

    def test_no_device_info_flag(self, parser):
        raw = make_raw(service_uuids=[DEXCOM_G6_SERVICE_UUID])
        result = parser.parse(raw)
        assert result.metadata.get("has_device_info") is not True


class TestDexcomNoMatch:
    def test_unrelated_uuid(self, parser):
        raw = make_raw(service_uuids=["1234"], local_name="SomeDevice")
        assert parser.parse(raw) is None

    def test_empty_ad(self, parser):
        raw = make_raw()
        assert parser.parse(raw) is None

    def test_plain_dex_name_does_not_match(self, parser):
        # "DEX" alone isn't in the documented Dexcom name format.
        raw = make_raw(local_name="DEX")
        assert parser.parse(raw) is None

    def test_dexcom_prefix_but_wrong_length(self, parser):
        # "DexcomABC" is 9 chars — G6 format is exactly 8 (Dexcom + 2).
        raw = make_raw(local_name="DexcomABC")
        assert parser.parse(raw) is None


class TestDexcomSteloEnrichment:
    """apk-ble-hunting/reports/dexcom-stelo_passive.md.

    Stelo is an OTC G7-class biosensor that reuses the G7 transmitter BLE stack
    and its advertising service UUID, so it is the same passive fingerprint as
    the G7 — the plugin flags the shared family rather than claiming a model it
    cannot distinguish. The report also documents Dexcom's SIG company ID
    0x00D0, which the app never filters on but which is a valid passive vendor
    signal.
    """

    def test_g7_uuid_reports_shared_product_family(self, parser):
        raw = make_raw(service_uuids=[DEXCOM_G7_SERVICE_UUID])
        result = parser.parse(raw)
        assert result.metadata["model"] == "G7"
        assert result.metadata["product_family"] == "G7-class (G7 / ONE+ / Stelo)"

    def test_g7_name_prefix_reports_shared_product_family(self, parser):
        result = parser.parse(make_raw(local_name="DXCMXYZ123"))
        assert result.metadata["product_family"] == "G7-class (G7 / ONE+ / Stelo)"

    def test_g6_has_no_product_family(self, parser):
        result = parser.parse(make_raw(service_uuids=[DEXCOM_G6_SERVICE_UUID]))
        assert "product_family" not in result.metadata

    def test_company_id_matches_in_registry(self):
        from adwatch.registry import ParserRegistry, register_parser
        from adwatch.plugins.dexcom_cgm import DEXCOM_COMPANY_ID

        registry = ParserRegistry()

        @register_parser(
            name="dexcom_cgm",
            company_id=DEXCOM_COMPANY_ID,
            description="Dexcom",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class _P(DexcomCgmParser):
            pass

        raw = make_raw(manufacturer_data=bytes.fromhex("d0000102"))
        assert len(registry.match(raw)) == 1

    def test_company_id_only_ad_parses_as_unknown_model(self, parser):
        raw = make_raw(manufacturer_data=bytes.fromhex("d0000102"))
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["vendor"] == "Dexcom"
        assert result.metadata["model"] == "unknown"
        assert result.raw_payload_hex == "d0000102"

    def test_other_company_id_does_not_parse(self, parser):
        raw = make_raw(manufacturer_data=bytes.fromhex("4c000102"))
        assert parser.parse(raw) is None

    def test_vendor_set_for_uuid_matches_too(self, parser):
        result = parser.parse(make_raw(service_uuids=[DEXCOM_G6_SERVICE_UUID]))
        assert result.metadata["vendor"] == "Dexcom"
