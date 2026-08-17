"""Tests for the Hailie / Adherium SmartChat inhaler-sensor plugin.

Byte layouts per apk-ble-hunting/reports/smartinhalerlive_passive.md.
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.hailie_adherium import (
    HailieParser,
    ADHERIUM_COMPANY_ID,
    HAILIE_SIG_SERVICE_UUID,
    HAILIE_LEGACY_SERVICE_UUID,
)


def _make_ad(**kw):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "D4:11:22:33:44:55",
        "address_type": "random",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _mfr(version=1, flags=0x80, battery=95, last_sync=800000000,
         model=109, serial=b"ADH1234567"):
    return (
        bytes([0xA2, 0x05, version, flags, battery])
        + last_sync.to_bytes(4, "little")
        + model.to_bytes(2, "little")
        + serial
    )


def _register(registry):
    @register_parser(
        name="hailie_adherium",
        company_id=ADHERIUM_COMPANY_ID,
        service_uuid=[HAILIE_SIG_SERVICE_UUID, HAILIE_LEGACY_SERVICE_UUID],
        description="Hailie",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(HailieParser):
        pass

    return _P


class TestHailieMatching:
    def test_matches_adherium_company_id(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(manufacturer_data=_mfr()))) == 1

    def test_matches_sig_service_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[HAILIE_SIG_SERVICE_UUID])
        assert len(registry.match(ad)) == 1

    def test_matches_short_sig_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(service_uuids=["fdfe"]))) == 1

    def test_matches_legacy_128bit_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[HAILIE_LEGACY_SERVICE_UUID])
        assert len(registry.match(ad)) == 1

    def test_unrelated_ad_does_not_match(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=bytes([0x4C, 0x00, 0x02, 0x15]))
        assert registry.match(ad) == []


class TestHailieManufacturerDecode:
    def test_decodes_full_payload(self):
        result = HailieParser().parse(_make_ad(manufacturer_data=_mfr()))
        assert result is not None
        assert result.metadata["protocol_version"] == 1
        assert result.metadata["battery_percent"] == 95
        assert result.metadata["serial"] == "ADH1234567"
        assert result.metadata["hardware_model"] == "NF0109"
        assert result.metadata["model_code"] == 109
        assert result.metadata["last_sync_offset_s"] == 800000000
        assert result.metadata["last_sync_time"] == "2025-05-08T06:13:20Z"
        assert result.metadata["never_synced"] is False
        assert result.metadata["generation"] == "smartchat_v1"

    def test_mode_1_from_bit7(self):
        result = HailieParser().parse(_make_ad(manufacturer_data=_mfr(flags=0x80)))
        assert result.metadata["mode"] == 1

    def test_mode_2_from_bit6(self):
        result = HailieParser().parse(_make_ad(manufacturer_data=_mfr(flags=0x40)))
        assert result.metadata["mode"] == 2

    def test_mode_3_when_neither_bit_set(self):
        result = HailieParser().parse(_make_ad(manufacturer_data=_mfr(flags=0x00)))
        assert result.metadata["mode"] == 3

    def test_bit7_wins_over_bit6(self):
        result = HailieParser().parse(_make_ad(manufacturer_data=_mfr(flags=0xC0)))
        assert result.metadata["mode"] == 1

    def test_flags_byte_recorded(self):
        result = HailieParser().parse(_make_ad(manufacturer_data=_mfr(flags=0x41)))
        assert result.metadata["flags"] == 0x41

    def test_never_synced_when_offset_zero(self):
        result = HailieParser().parse(_make_ad(manufacturer_data=_mfr(last_sync=0)))
        assert result.metadata["never_synced"] is True
        assert "last_sync_time" not in result.metadata

    def test_model_zero_padded(self):
        result = HailieParser().parse(_make_ad(manufacturer_data=_mfr(model=7)))
        assert result.metadata["hardware_model"] == "NF0007"

    def test_serial_strips_non_alphanumeric(self):
        ad = _make_ad(manufacturer_data=_mfr(serial=b"ADH-12\x00 34"))
        result = HailieParser().parse(ad)
        assert result.metadata["serial"] == "ADH1234"

    def test_battery_percent_full_range(self):
        result = HailieParser().parse(_make_ad(manufacturer_data=_mfr(battery=0)))
        assert result.metadata["battery_percent"] == 0

    def test_wrong_protocol_version_not_decoded(self):
        ad = _make_ad(manufacturer_data=_mfr(version=2))
        result = HailieParser().parse(ad)
        assert result is not None
        assert result.metadata["protocol_version"] == 2
        assert result.metadata["generation"] == "legacy_firmware"
        assert "serial" not in result.metadata
        assert "battery_percent" not in result.metadata

    def test_truncated_payload_not_decoded(self):
        # version + flags + battery + partial timestamp only
        ad = _make_ad(manufacturer_data=bytes([0xA2, 0x05, 0x01, 0x80, 0x5F, 0x00]))
        result = HailieParser().parse(ad)
        assert result is not None
        assert "battery_percent" not in result.metadata

    def test_empty_serial_tolerated(self):
        ad = _make_ad(manufacturer_data=_mfr(serial=b""))
        result = HailieParser().parse(ad)
        assert result.metadata["battery_percent"] == 95
        assert "serial" not in result.metadata

    def test_wrong_company_id_ignored(self):
        ad = _make_ad(
            service_uuids=[HAILIE_SIG_SERVICE_UUID],
            manufacturer_data=bytes([0x4C, 0x00]) + _mfr()[2:],
        )
        result = HailieParser().parse(ad)
        assert result is not None
        assert "serial" not in result.metadata

    def test_returns_none_for_unrelated(self):
        ad = _make_ad(manufacturer_data=bytes([0x4C, 0x00, 0x02, 0x15]))
        assert HailieParser().parse(ad) is None


class TestHailieLegacyPath:
    def test_legacy_uuid_alone_detected(self):
        ad = _make_ad(service_uuids=[HAILIE_LEGACY_SERVICE_UUID])
        result = HailieParser().parse(ad)
        assert result is not None
        assert result.metadata["generation"] == "smartchat_legacy"
        assert "serial" not in result.metadata

    def test_sig_uuid_alone_detected(self):
        ad = _make_ad(service_uuids=["fdfe"])
        result = HailieParser().parse(ad)
        assert result is not None
        assert result.metadata["vendor"] == "Adherium"


class TestHailieIdentityAndBasics:
    def test_identity_from_serial(self):
        result = HailieParser().parse(_make_ad(manufacturer_data=_mfr()))
        expected = hashlib.sha256(b"hailie:ADH1234567").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_stable_across_mac_and_battery(self):
        a = _make_ad(manufacturer_data=_mfr(battery=90), mac_address="AA:BB:CC:DD:EE:FF")
        b = _make_ad(manufacturer_data=_mfr(battery=12), mac_address="11:22:33:44:55:66")
        assert HailieParser().parse(a).identifier_hash == \
            HailieParser().parse(b).identifier_hash

    def test_identity_falls_back_to_mac(self):
        ad = _make_ad(service_uuids=["fdfe"])
        result = HailieParser().parse(ad)
        expected = hashlib.sha256(
            f"hailie:{ad.mac_address}".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_basics(self):
        result = HailieParser().parse(_make_ad(manufacturer_data=_mfr()))
        assert result.parser_name == "hailie_adherium"
        assert result.beacon_type == "hailie_adherium"
        assert result.device_class == "medical"
        assert result.metadata["vendor"] == "Adherium"
        assert result.metadata["product"] == "Hailie inhaler sensor"

    def test_local_name_recorded(self):
        ad = _make_ad(service_uuids=["fdfe"], local_name="Hailie")
        assert HailieParser().parse(ad).metadata["device_name"] == "Hailie"

    def test_company_id_constant(self):
        assert ADHERIUM_COMPANY_ID == 0x05A2
