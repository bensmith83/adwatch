"""Tests for Microsoft CDP parser."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.parsers.microsoft_cdp import MicrosoftCDPParser


@pytest.fixture
def parser():
    return MicrosoftCDPParser()


def make_raw(manufacturer_data, **kwargs):
    defaults = dict(
        timestamp="2026-03-05T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        service_data=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(manufacturer_data=manufacturer_data, **defaults)


# Windows laptop: 06 00 01 2f ...
# version=1 (001), device_type=15 (01111) = laptop
# byte 3 = 0b001_01111 = 0x2F
LAPTOP_PAYLOAD = bytes([
    0x06, 0x00,  # Microsoft company ID (little-endian)
    0x01,        # Scenario type: Bluetooth connectivity
    0x2F,        # Version=1, Device type=15 (laptop)
    0x00, 0x01, 0x02, 0x03,  # Scenario-specific data
])

# Xbox: 06 00 01 21
# version=1 (001), device_type=1 (00001) = Xbox
XBOX_PAYLOAD = bytes([
    0x06, 0x00,  # Microsoft company ID
    0x01,        # Scenario type: Bluetooth connectivity
    0x21,        # Version=1, Device type=1 (Xbox)
    0xAA, 0xBB,
])

# Android via Microsoft apps: 06 00 01 28
# version=1 (001), device_type=8 (01000) = Android
ANDROID_PAYLOAD = bytes([
    0x06, 0x00,
    0x01,
    0x28,        # Version=1, Device type=8 (Android)
    0xCC, 0xDD,
])


class TestMicrosoftCDPParser:
    def test_parse_valid_cdp_laptop(self, parser):
        raw = make_raw(LAPTOP_PAYLOAD)
        result = parser.parse(raw)

        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(LAPTOP_PAYLOAD)
        result = parser.parse(raw)

        assert result.parser_name == "microsoft_cdp"

    def test_extracts_scenario_type(self, parser):
        raw = make_raw(LAPTOP_PAYLOAD)
        result = parser.parse(raw)

        assert result.metadata["scenario_type"] == 0x01

    def test_extracts_device_type_laptop(self, parser):
        raw = make_raw(LAPTOP_PAYLOAD)
        result = parser.parse(raw)

        assert result.metadata["device_type"] == 15

    def test_extracts_device_type_xbox(self, parser):
        raw = make_raw(XBOX_PAYLOAD)
        result = parser.parse(raw)

        assert result.metadata["device_type"] == 1

    def test_extracts_device_type_android(self, parser):
        raw = make_raw(ANDROID_PAYLOAD)
        result = parser.parse(raw)

        assert result.metadata["device_type"] == 8

    def test_identifier_hash_format(self, parser):
        raw = make_raw(LAPTOP_PAYLOAD)
        result = parser.parse(raw)

        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_identifier_hash_uses_mac_and_payload(self, parser):
        """Identity = SHA256(mac:payload_hex)[:16]."""
        raw = make_raw(LAPTOP_PAYLOAD, mac_address="AA:BB:CC:DD:EE:FF")
        result = parser.parse(raw)

        payload_hex = LAPTOP_PAYLOAD[2:].hex()  # everything after company ID
        expected = hashlib.sha256(
            f"AA:BB:CC:DD:EE:FF:{payload_hex}".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_raw_payload_hex_present(self, parser):
        raw = make_raw(LAPTOP_PAYLOAD)
        result = parser.parse(raw)

        assert result.raw_payload_hex
        assert isinstance(result.raw_payload_hex, str)

    def test_returns_none_for_wrong_company_id(self, parser):
        data = bytearray(LAPTOP_PAYLOAD)
        data[0] = 0x4C  # Apple instead of Microsoft
        raw = make_raw(bytes(data))

        assert parser.parse(raw) is None

    def test_returns_none_for_short_payload(self, parser):
        # Need at least 4 bytes (company_id + scenario + device_type)
        raw = make_raw(bytes([0x06, 0x00, 0x01]))
        assert parser.parse(raw) is None

    def test_returns_none_for_no_manufacturer_data(self, parser):
        raw = make_raw(None)
        assert parser.parse(raw) is None

    def test_returns_none_for_empty_manufacturer_data(self, parser):
        raw = make_raw(b"")
        assert parser.parse(raw) is None

    # ── New field tests (RED phase) ──────────────────────────────────

    # Full 29-byte payload: 2 company ID + 27 data bytes
    # Byte 0: scenario_type = 0x01
    # Byte 1: version_and_device_type = 0x29 → version=1 (001), device_type=9 (01001) = Win10 Desktop
    # Byte 2: version_and_flags = 0x01 → nearby_share_mode = 0x01 ("Everyone")
    # Byte 3: flags_and_device_status = 0x24 → bit5=1 (bt_addr_as_device_id=True), lower4=0x04 ("NearShareAuthPolicySameUser")
    # Bytes 4-7: salt = DE AD BE EF
    # Bytes 8-26: device_hash = 19 bytes of 0xAA

    FULL_PAYLOAD = bytes([
        0x06, 0x00,  # Microsoft company ID
        0x01,        # scenario_type
        0x29,        # version=1, device_type=9 (Win10 Desktop)
        0x01,        # nearby_share_mode = Everyone
        0x24,        # bt_addr_as_device_id=True, extended_status=0x04
        0xDE, 0xAD, 0xBE, 0xEF,  # salt
    ] + [0xAA] * 19)  # device_hash (19 bytes)

    def test_device_type_name_desktop(self, parser):
        raw = make_raw(self.FULL_PAYLOAD)
        result = parser.parse(raw)
        assert result.metadata["device_type_name"] == "Windows 10 Desktop"

    def test_device_type_name_laptop(self, parser):
        raw = make_raw(LAPTOP_PAYLOAD)
        result = parser.parse(raw)
        assert result.metadata["device_type_name"] == "Windows laptop"

    def test_device_type_name_xbox(self, parser):
        raw = make_raw(XBOX_PAYLOAD)
        result = parser.parse(raw)
        assert result.metadata["device_type_name"] == "Xbox One"

    def test_device_type_name_android(self, parser):
        raw = make_raw(ANDROID_PAYLOAD)
        result = parser.parse(raw)
        assert result.metadata["device_type_name"] == "Android device"

    def test_device_type_name_unknown(self, parser):
        payload = bytes([0x06, 0x00, 0x01, 0x3F, 0x00, 0x00])  # device_type=31
        raw = make_raw(payload)
        result = parser.parse(raw)
        assert result.metadata["device_type_name"] == "Unknown"

    def test_version_extracted(self, parser):
        raw = make_raw(self.FULL_PAYLOAD)
        result = parser.parse(raw)
        # 0x29 >> 5 = 1
        assert result.metadata["version"] == 1

    def test_version_zero(self, parser):
        # version_and_device_type = 0x09 → version=0, device_type=9
        payload = bytes([0x06, 0x00, 0x01, 0x09, 0x00, 0x00])
        raw = make_raw(payload)
        result = parser.parse(raw)
        assert result.metadata["version"] == 0

    def test_nearby_share_mode_everyone(self, parser):
        raw = make_raw(self.FULL_PAYLOAD)
        result = parser.parse(raw)
        assert result.metadata["nearby_share_mode"] == "Everyone"

    def test_nearby_share_mode_my_devices_only(self, parser):
        # Byte 2 = 0x00 → "My devices only"
        payload = bytearray(self.FULL_PAYLOAD)
        payload[4] = 0x00  # byte 2 of CDP payload
        raw = make_raw(bytes(payload))
        result = parser.parse(raw)
        assert result.metadata["nearby_share_mode"] == "My devices only"

    def test_nearby_share_mode_unknown(self, parser):
        # Byte 2 = 0x05 → unknown share mode
        payload = bytearray(self.FULL_PAYLOAD)
        payload[4] = 0x05
        raw = make_raw(bytes(payload))
        result = parser.parse(raw)
        assert result.metadata["nearby_share_mode"] == "Unknown"

    def test_bt_address_as_device_id_true(self, parser):
        raw = make_raw(self.FULL_PAYLOAD)
        result = parser.parse(raw)
        # Byte 3 = 0x24, bit 5 = 1
        assert result.metadata["bt_address_as_device_id"] is True

    def test_bt_address_as_device_id_false(self, parser):
        payload = bytearray(self.FULL_PAYLOAD)
        payload[5] = 0x04  # bit 5 = 0, lower 4 = 0x04
        raw = make_raw(bytes(payload))
        result = parser.parse(raw)
        assert result.metadata["bt_address_as_device_id"] is False

    def test_extended_device_status_single_flag(self, parser):
        raw = make_raw(self.FULL_PAYLOAD)
        result = parser.parse(raw)
        # Byte 3 = 0x24 → lower 4 bits = 0x4 → NearShareAuthPolicySameUser
        assert result.metadata["extended_device_status"] == ["NearShareAuthPolicySameUser"]

    def test_extended_device_status_multiple_flags(self, parser):
        payload = bytearray(self.FULL_PAYLOAD)
        payload[5] = 0x29  # bit5=1, lower4 = 0x09 = 0x01|0x08
        raw = make_raw(bytes(payload))
        result = parser.parse(raw)
        status = result.metadata["extended_device_status"]
        assert "RemoteSessionsHosted" in status
        assert "NearShareAuthPolicyPermissive" in status
        assert len(status) == 2

    def test_extended_device_status_empty(self, parser):
        payload = bytearray(self.FULL_PAYLOAD)
        payload[5] = 0x20  # bit5=1, lower4 = 0x00
        raw = make_raw(bytes(payload))
        result = parser.parse(raw)
        assert result.metadata["extended_device_status"] == []

    def test_salt_hex(self, parser):
        raw = make_raw(self.FULL_PAYLOAD)
        result = parser.parse(raw)
        assert result.metadata["salt_hex"] == "deadbeef"

    def test_device_hash_hex(self, parser):
        raw = make_raw(self.FULL_PAYLOAD)
        result = parser.parse(raw)
        assert result.metadata["device_hash_hex"] == "aa" * 19

    def test_salt_hex_absent_for_short_payload(self, parser):
        # Only 4 bytes after company ID — not enough for salt
        raw = make_raw(LAPTOP_PAYLOAD)
        result = parser.parse(raw)
        assert "salt_hex" not in result.metadata

    def test_device_hash_hex_absent_for_short_payload(self, parser):
        raw = make_raw(LAPTOP_PAYLOAD)
        result = parser.parse(raw)
        assert "device_hash_hex" not in result.metadata

    def test_device_class_xbox(self, parser):
        raw = make_raw(XBOX_PAYLOAD)
        result = parser.parse(raw)
        assert result.device_class == "gaming_console"

    def test_device_class_android_phone(self, parser):
        raw = make_raw(ANDROID_PAYLOAD)
        result = parser.parse(raw)
        assert result.device_class == "phone"

    def test_device_class_desktop(self, parser):
        raw = make_raw(self.FULL_PAYLOAD)
        result = parser.parse(raw)
        assert result.device_class == "computer"

    def test_device_class_laptop(self, parser):
        raw = make_raw(LAPTOP_PAYLOAD)
        result = parser.parse(raw)
        assert result.device_class == "laptop"

    def test_device_class_ipad(self, parser):
        # device_type=7 → Apple iPad → "tablet"
        payload = bytes([0x06, 0x00, 0x01, 0x27, 0x00, 0x00])
        raw = make_raw(payload)
        result = parser.parse(raw)
        assert result.device_class == "tablet"

    def test_device_class_iot(self, parser):
        # device_type=13 → Windows IoT → "iot"
        payload = bytes([0x06, 0x00, 0x01, 0x2D, 0x00, 0x00])
        raw = make_raw(payload)
        result = parser.parse(raw)
        assert result.device_class == "iot"

    def test_device_class_linux(self, parser):
        # device_type=12 → Linux → "computer"
        payload = bytes([0x06, 0x00, 0x01, 0x2C, 0x00, 0x00])
        raw = make_raw(payload)
        result = parser.parse(raw)
        assert result.device_class == "computer"

    def test_device_class_surface_hub(self, parser):
        # device_type=14 → Surface Hub → "computer"
        payload = bytes([0x06, 0x00, 0x01, 0x2E, 0x00, 0x00])
        raw = make_raw(payload)
        result = parser.parse(raw)
        assert result.device_class == "computer"

    def test_device_class_windows_tablet(self, parser):
        # device_type=16 → Windows tablet → "tablet"
        payload = bytes([0x06, 0x00, 0x01, 0x30, 0x00, 0x00])
        raw = make_raw(payload)
        result = parser.parse(raw)
        assert result.device_class == "tablet"

    def test_device_class_iphone(self, parser):
        # device_type=6 → Apple iPhone → "phone"
        payload = bytes([0x06, 0x00, 0x01, 0x26, 0x00, 0x00])
        raw = make_raw(payload)
        result = parser.parse(raw)
        assert result.device_class == "phone"

    def test_device_class_windows_phone(self, parser):
        # device_type=11 → Windows 10 Phone → "phone"
        payload = bytes([0x06, 0x00, 0x01, 0x2B, 0x00, 0x00])
        raw = make_raw(payload)
        result = parser.parse(raw)
        assert result.device_class == "phone"


class TestMicrosoftCDPUIConfig:
    def test_has_ui_config(self, parser):
        cfg = parser.ui_config()
        assert cfg is not None

    def test_tab_name(self, parser):
        cfg = parser.ui_config()
        assert cfg.tab_name == "Microsoft CDP"

    def test_has_widgets(self, parser):
        cfg = parser.ui_config()
        assert len(cfg.widgets) >= 1

    def test_widget_type_is_data_table(self, parser):
        cfg = parser.ui_config()
        assert cfg.widgets[0].widget_type == "data_table"

    def test_widget_has_render_hints_with_columns(self, parser):
        cfg = parser.ui_config()
        columns = cfg.widgets[0].render_hints.get("columns", [])
        assert "device_type_name" in columns
        assert "nearby_share_mode" in columns
        assert "device_class" in columns


class TestMicrosoftCDPApiRouter:
    def test_has_api_router(self, parser):
        router = parser.api_router(db=None)
        # Returns None when no db, that's fine
        assert router is None

    def test_api_router_returns_router_with_db(self, parser):
        class FakeDB:
            async def fetchall(self, sql, params=()):
                return []
        router = parser.api_router(db=FakeDB())
        assert router is not None

    def test_has_storage_schema(self, parser):
        assert parser.storage_schema() is None
