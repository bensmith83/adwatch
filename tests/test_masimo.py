"""Tests for the Masimo plugin (MightySat + Stork family).

Stork enrichment per apk-ble-hunting/reports/masimo-stork_passive.md:
company ID 0x0243 + per-module Stork service UUIDs. The app parses no
manufacturer-data bytes, so only presence/device-type is decoded.
"""

import hashlib
import struct

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.masimo import (
    MasimoParser,
    MASIMO_COMPANY_ID,
    STORK_STK_SERVICE_UUID,
    STORK_SENSOR_SERVICE_UUID,
    STORK_SERVICE_UUIDS,
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


def _mfr(payload: bytes = b"", company_id: int = MASIMO_COMPANY_ID) -> bytes:
    return struct.pack("<H", company_id) + payload


def _register(registry):
    @register_parser(
        name="masimo",
        company_id=MASIMO_COMPANY_ID,
        service_uuid=list(STORK_SERVICE_UUIDS),
        local_name_pattern=r"(?i)^(MightySat|Masimo|STK)",
        description="Masimo",
        version="1.1.0",
        core=False,
        registry=registry,
    )
    class _P(MasimoParser):
        pass

    return _P


class TestMasimoConstants:
    def test_company_id(self):
        assert MASIMO_COMPANY_ID == 0x0243

    def test_stork_service_uuids_lowercase(self):
        assert STORK_STK_SERVICE_UUID == "913e1000-599e-4f9c-86b3-4b1ca8d24a30"
        assert STORK_SENSOR_SERVICE_UUID == "76c01000-3c37-42dc-b66f-888dea4dca72"
        assert set(STORK_SERVICE_UUIDS) == {
            STORK_STK_SERVICE_UUID,
            STORK_SENSOR_SERVICE_UUID,
        }


class TestMasimoMatching:
    def test_match_company_id(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(manufacturer_data=_mfr(b"\x01")))) == 1

    def test_match_stork_stk_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[STORK_STK_SERVICE_UUID.upper()])
        assert len(registry.match(ad)) == 1

    def test_match_stork_sensor_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[STORK_SENSOR_SERVICE_UUID])
        assert len(registry.match(ad)) == 1

    def test_no_match_unrelated(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=_mfr(b"\x01", company_id=0x004C),
                      local_name="Random Device")
        assert registry.match(ad) == []


class TestMasimoParse:
    def test_mightysat_name_still_parses(self):
        result = MasimoParser().parse(_make_ad(local_name="MightySat Rx"))
        assert result is not None
        assert result.device_class == "medical"
        assert result.metadata["device_name"] == "MightySat Rx"

    def test_company_id_only_still_parses(self):
        result = MasimoParser().parse(_make_ad(manufacturer_data=_mfr(b"\x01\x02")))
        assert result is not None
        assert result.metadata["protocol_version"] == 0x01
        assert result.metadata["payload_hex"] == "0102"

    def test_stork_stk_uuid_alone_parses(self):
        result = MasimoParser().parse(
            _make_ad(service_uuids=[STORK_STK_SERVICE_UUID])
        )
        assert result is not None
        assert result.device_class == "medical"
        assert result.metadata["product_family"] == "stork"
        assert result.metadata["stork_module"] == "STK"

    def test_stork_sensor_uuid_parses_module(self):
        result = MasimoParser().parse(
            _make_ad(service_uuids=[STORK_SENSOR_SERVICE_UUID.upper()])
        )
        assert result is not None
        assert result.metadata["stork_module"] == "STORK_SENSOR"

    def test_stork_uuid_with_company_id(self):
        result = MasimoParser().parse(
            _make_ad(
                manufacturer_data=_mfr(b"\xaa\xbb"),
                service_uuids=[STORK_STK_SERVICE_UUID],
            )
        )
        assert result is not None
        assert result.metadata["stork_module"] == "STK"
        assert result.metadata["cid_match"] is True
        assert result.metadata["payload_hex"] == "aabb"

    def test_company_id_without_stork_uuid_has_no_module(self):
        result = MasimoParser().parse(_make_ad(manufacturer_data=_mfr(b"\x01")))
        assert "stork_module" not in result.metadata

    def test_identity_hash_mac_based(self):
        result = MasimoParser().parse(_make_ad(service_uuids=[STORK_STK_SERVICE_UUID]))
        expected = hashlib.sha256(b"masimo:AA:BB:CC:DD:EE:FF").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_no_signal_returns_none(self):
        assert MasimoParser().parse(_make_ad(local_name="Some Phone")) is None

    def test_short_manufacturer_data_no_crash(self):
        result = MasimoParser().parse(
            _make_ad(manufacturer_data=b"\x43\x02", service_uuids=[])
        )
        assert result is not None
        assert "payload_hex" not in result.metadata
