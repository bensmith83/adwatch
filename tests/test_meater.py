"""Tests for MEATER wireless meat thermometer plugin.

Identifier tables and parsing paths per
apk-ble-hunting/reports/apptionlabs-meater-app_passive.md.
"""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.meater import (
    MEATERParser,
    MEATER_COMPANY_ID,
    PROBE_SERVICE_UUIDS,
    BLOCK_NORMAL_UUID,
    BLOCK_KEEPALIVE_UUIDS,
    PRODUCT_TYPES,
    BLOCK_STATUS_MODES,
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


def _mfr(payload: bytes) -> bytes:
    return struct.pack("<H", MEATER_COMPANY_ID) + payload


def _register(registry):
    all_uuids = [BLOCK_NORMAL_UUID] + list(BLOCK_KEEPALIVE_UUIDS) + list(PROBE_SERVICE_UUIDS)

    @register_parser(
        name="meater",
        company_id=MEATER_COMPANY_ID,
        service_uuid=all_uuids,
        local_name_pattern=r"^MEATER|^[0-9a-fA-F]{2}-[0-9a-fA-F]+$",
        description="MEATER",
        version="1.1.0",
        core=False,
        registry=registry,
    )
    class _P(MEATERParser):
        pass

    return _P


class TestMEATERConstants:
    def test_company_id(self):
        assert MEATER_COMPANY_ID == 0x037B

    def test_probe_uuid_count(self):
        # V1, V2 (flag-gated), MEATER+ V2, MEATER+ SE.
        assert len(PROBE_SERVICE_UUIDS) == 4

    def test_block_keepalive_uuid_count(self):
        # Keep-alive + Gen2 block + 4 Gen3 block variants.
        assert len(BLOCK_KEEPALIVE_UUIDS) == 6

    def test_product_type_block_is_8(self):
        assert PRODUCT_TYPES[8] == "BLOCK"

    def test_product_type_original_probe_is_0(self):
        assert PRODUCT_TYPES[0] == "PROBE"

    def test_product_type_gen2_plus_pro(self):
        assert PRODUCT_TYPES[113] == "SECOND_GENERATION_PLUS_PRO"

    def test_status_mode_wifi_client(self):
        assert BLOCK_STATUS_MODES[9] == "WiFi Client"


class TestMEATERMatching:
    def test_match_company_id(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=_mfr(b"\x01" * 8))
        assert len(registry.match(ad)) == 1

    def test_match_probe_v1_service_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=["a75cc7fc-c956-488f-ac2a-2dbc08b63a04"])
        assert len(registry.match(ad)) == 1

    def test_match_block_normal_service_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[BLOCK_NORMAL_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_block_gen3_keepalive(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=["7cf05643-1430-4be6-a0a8-b1e2d95462ba"])
        assert len(registry.match(ad)) == 1

    def test_match_local_name_meater(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="MEATER Probe")
        assert len(registry.match(ad)) == 1

    def test_match_name_fallback_hex_format(self):
        # "00-1A2B3C4D5E6F" fallback per passive-report section.
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="00-1A2B3C4D5E6F")
        assert len(registry.match(ad)) == 1


class TestMEATERProbeParsing:
    def _parse(self, **kwargs):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(**kwargs)
        matched = registry.match(ad)
        assert matched
        return matched[0].parse(ad)

    def test_probe_path_extracts_product_type_and_device_id(self):
        device_id_bytes = bytes.fromhex("1122334455667788")
        payload = bytes([0x00]) + device_id_bytes  # V1 PROBE
        result = self._parse(
            manufacturer_data=_mfr(payload),
            service_uuids=["a75cc7fc-c956-488f-ac2a-2dbc08b63a04"],
        )
        assert result.metadata["product_type_code"] == 0
        assert result.metadata["product_type"] == "PROBE"
        assert result.metadata["device_id"] == int.from_bytes(device_id_bytes, "little")
        assert result.metadata["device_id_hex"] == device_id_bytes[::-1].hex()

    def test_probe_gen2_plus_pro(self):
        payload = bytes([113]) + bytes(8)  # SECOND_GENERATION_PLUS_PRO
        result = self._parse(
            manufacturer_data=_mfr(payload),
            service_uuids=["c9e2746c-59f1-4e54-a0dd-e1e54555cf8b"],
        )
        assert result.metadata["product_type"] == "SECOND_GENERATION_PLUS_PRO"

    def test_probe_path_short_payload_yields_no_device_id(self):
        # <9 bytes → can't fill product_type+device_id; should gracefully skip.
        result = self._parse(
            manufacturer_data=_mfr(b"\x01\x02\x03"),
            service_uuids=["a75cc7fc-c956-488f-ac2a-2dbc08b63a04"],
        )
        assert "device_id" not in result.metadata


class TestMEATERBlockParsing:
    def _parse(self, **kwargs):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(**kwargs)
        matched = registry.match(ad)
        assert matched
        return matched[0].parse(ad)

    def test_block_normal_path_no_product_type_byte(self):
        # Normal block: 8 bytes = device_id only, product_type hardcoded 8.
        device_id_bytes = bytes.fromhex("aabbccddeeff0011")
        result = self._parse(
            manufacturer_data=_mfr(device_id_bytes),
            service_uuids=[BLOCK_NORMAL_UUID],
        )
        assert result.metadata["product_type_code"] == 8
        assert result.metadata["product_type"] == "BLOCK"
        assert result.metadata["device_id"] == int.from_bytes(device_id_bytes, "little")

    def test_block_keepalive_path_extracts_status_mode(self):
        # Keep-alive: product_type(1) + device_id(8) + status(1).
        payload = bytes([8]) + bytes(8) + bytes([9])  # BLOCK + WiFi Client
        result = self._parse(
            manufacturer_data=_mfr(payload),
            service_uuids=["24b299d9-61f7-48ba-86e0-f459dad3fc87"],
        )
        assert result.metadata["product_type"] == "BLOCK"
        assert result.metadata["status_mode_code"] == 9
        assert result.metadata["status_mode"] == "WiFi Client"

    def test_block_keepalive_probe_pairing_mode(self):
        payload = bytes([8]) + bytes(8) + bytes([12])
        result = self._parse(
            manufacturer_data=_mfr(payload),
            service_uuids=["b7107bbe-da2a-4124-b2cc-aafd624b61ce"],
        )
        assert result.metadata["status_mode"] == "Probe Pairing"

    def test_block_keepalive_gen3_uuid(self):
        payload = bytes([177]) + bytes(8) + bytes([9])  # Gen3 1x Gen1 probe
        result = self._parse(
            manufacturer_data=_mfr(payload),
            service_uuids=["9e09e66c-78dc-4e28-80c3-f7eb5194daaf"],
        )
        assert result.metadata["product_type"] == "THIRD_GENERATION_ONE_FIRST_GEN_PROBE_BLOCK"


class TestMEATERNameFallback:
    def _parse(self, **kwargs):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(**kwargs)
        matched = registry.match(ad)
        assert matched
        return matched[0].parse(ad)

    def test_name_fallback_extracts_product_type_and_id(self):
        result = self._parse(local_name="00-1A2B3C4D5E6F")
        assert result.metadata["product_type_code"] == 0
        assert result.metadata["product_type"] == "PROBE"
        assert result.metadata["device_id_hex"] == "1a2b3c4d5e6f"

    def test_name_fallback_gen2_probe(self):
        result = self._parse(local_name="10-DEADBEEF")  # 0x10 = 16 = Gen2 probe
        assert result.metadata["product_type"] == "SECOND_GENERATION_PROBE"


class TestMEATERIdentity:
    def _parse(self, **kwargs):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(**kwargs)
        matched = registry.match(ad)
        assert matched
        return matched[0].parse(ad)

    def test_identity_hash_uses_device_id_when_available(self):
        device_id_bytes = bytes.fromhex("1122334455667788")
        payload = bytes([0x00]) + device_id_bytes
        result = self._parse(
            manufacturer_data=_mfr(payload),
            service_uuids=["a75cc7fc-c956-488f-ac2a-2dbc08b63a04"],
            mac_address="11:22:33:44:55:66",
        )
        expected = hashlib.sha256(
            f"meater:{int.from_bytes(device_id_bytes, 'little')}".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_fallback_without_device_id(self):
        ad_kwargs = dict(local_name="MEATER", mac_address="11:22:33:44:55:66")
        result = self._parse(**ad_kwargs)
        expected = hashlib.sha256("11:22:33:44:55:66:MEATER".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_parse_result_fields(self):
        result = self._parse(
            manufacturer_data=_mfr(b"\x00" + bytes(8)),
            service_uuids=["a75cc7fc-c956-488f-ac2a-2dbc08b63a04"],
        )
        assert result.parser_name == "meater"
        assert result.beacon_type == "meater"
        assert result.device_class == "sensor"
