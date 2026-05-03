"""Tests for CANDY HOUSE SESAME smart-lock family plugin.

Byte layouts and product enum per
apk-ble-hunting/reports/candyhouse-sesame2_passive.md.
"""

import base64
import hashlib

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.candyhouse_sesame import (
    CandyHouseSesameParser,
    SESAME_SERVICE_UUID,
    PRODUCT_MODELS,
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


def _register(registry):
    @register_parser(
        name="candyhouse_sesame",
        service_uuid=SESAME_SERVICE_UUID,
        description="CANDY HOUSE SESAME",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(CandyHouseSesameParser):
        pass

    return _P


def _mfr_only(payload: bytes) -> bytes:
    """Build manufacturer_data without a real company-ID prefix.

    SESAME does not use a SIG company ID — it relies on the FD81 service-UUID
    filter, then reads valueAt(0). For the test we provide a 2-byte prefix so
    the framework accepts it as mfr-data; the parser reads from
    manufacturer_payload (offset 2+).
    """
    return b"\x00\x00" + payload


class TestSesameConstants:
    def test_service_uuid(self):
        assert SESAME_SERVICE_UUID == "fd81"

    def test_models_contains_known_codes(self):
        assert PRODUCT_MODELS[1] == "WM2"
        assert PRODUCT_MODELS[2] == "Hub3"
        assert PRODUCT_MODELS[8] == "SS5"
        assert PRODUCT_MODELS[9] == "SS5PRO"
        assert PRODUCT_MODELS[34] == "SSM_MIWA"

    def test_model_count_at_least_34(self):
        assert max(PRODUCT_MODELS.keys()) >= 34


class TestSesameMatching:
    def test_match_service_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[SESAME_SERVICE_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_full_service_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=["0000fd81-0000-1000-8000-00805f9b34fb"])
        assert len(registry.match(ad)) == 1


class TestSesameModelDecoding:
    def _parse(self, payload: bytes, **extra):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(
            manufacturer_data=_mfr_only(payload),
            service_uuids=[SESAME_SERVICE_UUID],
            **extra,
        )
        matched = registry.match(ad)
        assert matched
        return matched[0].parse(ad)

    def test_decodes_product_model_byte(self):
        # Model 8 = SS5. Plus 16 bytes device-ID tail.
        payload = bytes([8]) + bytes(16) + bytes([0])
        result = self._parse(payload)
        assert result.metadata["product_model_code"] == 8
        assert result.metadata["product_model"] == "SS5"

    def test_unknown_model_falls_through(self):
        payload = bytes([200]) + bytes(20)
        result = self._parse(payload)
        assert result.metadata["product_model_code"] == 200
        assert result.metadata["product_model"].startswith("UNKNOWN")

    def test_registration_bit_for_non_hub3(self):
        # SS5: registered bit lives in advBytes[2] bit 0.
        payload_unreg = bytes([8, 0x00, 0x00]) + bytes(16)
        payload_reg = bytes([8, 0x00, 0x01]) + bytes(16)
        r_unreg = self._parse(payload_unreg)
        r_reg = self._parse(payload_reg)
        assert r_unreg.metadata["is_registered"] is False
        assert r_reg.metadata["is_registered"] is True

    def test_registration_bit_for_hub3(self):
        # Hub3 (model 2): registered bit in advBytes[1] bit 0.
        payload_reg = bytes([2, 0x01, 0x00]) + bytes(8)
        result = self._parse(payload_reg)
        assert result.metadata["product_model"] == "Hub3"
        assert result.metadata["is_registered"] is True

    def test_adv_tag_b1_bit(self):
        # Bit 1 of advBytes[2] is adv_tag_b1.
        payload = bytes([8, 0x00, 0x02]) + bytes(16)
        result = self._parse(payload)
        assert result.metadata["adv_tag_b1"] is True


class TestSesameDeviceID:
    def _parse(self, payload: bytes, **extra):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(
            manufacturer_data=_mfr_only(payload),
            service_uuids=[SESAME_SERVICE_UUID],
            **extra,
        )
        matched = registry.match(ad)
        assert matched
        return matched[0].parse(ad)

    def test_os3_family_extracts_16byte_device_id(self):
        # SS5 (model 8): device-ID is bytes[3..18] (16 bytes).
        device_id = bytes(range(16))
        payload = bytes([8, 0x00, 0x01]) + device_id
        result = self._parse(payload)
        assert result.metadata["device_id_hex"] == device_id.hex()

    def test_hub3_extracts_8byte_device_id(self):
        # Hub3: bytes[2..9] (8 bytes).
        # Index [2..9] inclusive = 8 bytes
        device_id = bytes([0xAA] * 8)
        payload = bytes([2, 0x01]) + device_id
        result = self._parse(payload)
        assert result.metadata["device_id_hex"] == device_id.hex()

    def test_wm2_extracts_9byte_device_id(self):
        # WM2 (model 1): bytes[3..11] (9 bytes).
        device_id = bytes([0xBB] * 9)
        payload = bytes([1, 0x00, 0x00]) + device_id
        result = self._parse(payload)
        assert result.metadata["device_id_hex"] == device_id.hex()

    def test_os2_family_extracts_id_from_device_name(self):
        # SS2 (model 4): device-ID is base64-decoded from local_name.
        raw_id = bytes(range(12))  # any short blob
        encoded = base64.b64encode(raw_id).decode().rstrip("=")
        payload = bytes([4, 0x00, 0x00]) + bytes(8)
        result = self._parse(payload, local_name=encoded)
        assert result.metadata["device_id_hex"] == raw_id.hex()


class TestSesameIdentity:
    def _parse(self, payload: bytes, **extra):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(
            manufacturer_data=_mfr_only(payload),
            service_uuids=[SESAME_SERVICE_UUID],
            **extra,
        )
        matched = registry.match(ad)
        assert matched
        return matched[0].parse(ad)

    def test_identity_uses_in_advert_device_id(self):
        device_id = bytes(range(16))
        payload = bytes([8, 0x00, 0x01]) + device_id
        result = self._parse(payload, mac_address="11:22:33:44:55:66")
        expected = hashlib.sha256(f"sesame:{device_id.hex()}".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_parse_result_basics(self):
        payload = bytes([8]) + bytes(20)
        result = self._parse(payload)
        assert result.parser_name == "candyhouse_sesame"
        assert result.beacon_type == "candyhouse_sesame"
        assert result.device_class == "lock"
