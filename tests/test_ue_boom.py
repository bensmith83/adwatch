"""Tests for the Ultimate Ears (Logitech) BOOM / MEGABOOM / WONDERBOOM plugin.

Byte layout per apk-ble-hunting/reports/ue-boom_passive.md. The report's
offsets are relative to the FULL scan record; the manufacturer-data AD starts
at record offset 10 (`10 FF`), the Logitech company ID sits at 12-13
(`DA 01` LE = 0x01DA), so ``manufacturer_payload`` index 0 == record offset 14.
"""

import hashlib

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.ue_boom import (
    UEBoomParser,
    UE_SERVICE_UUID,
    LOGITECH_COMPANY_ID,
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


def _register(registry):
    @register_parser(
        name="ue_boom",
        company_id=LOGITECH_COMPANY_ID,
        service_uuid=UE_SERVICE_UUID,
        description="UE BOOM",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(UEBoomParser):
        pass

    return _P


def _cpp_payload(
    battery=85,
    powered=True,
    flags_hi=0x00,
    volume=0x0A,
    events=0x00,
    status=0xD4,
    extra=0x7A,
    broadcast_mac=b"\x11\x22\x33\x44\x55\x66",
    tail=0x05,
):
    """13-byte manufacturer payload (record offsets 14..26)."""
    b0 = (0x80 if powered else 0x00) | (battery & 0x7F)
    return bytes([b0, flags_hi, volume, events, status, extra]) + broadcast_mac + bytes([tail])


def _mfr(payload, cid=LOGITECH_COMPANY_ID):
    return cid.to_bytes(2, "little") + payload


def _wasp_payload(status=0xC5, pid=0x030D):
    body = bytearray(13)
    body[0] = (pid >> 8) & 0xFF
    body[1] = pid & 0xFF
    body[9] = status
    return bytes(body)


class TestUEBoomMatching:
    def test_matches_on_service_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[UE_SERVICE_UUID])
        assert len(registry.match(ad)) == 1

    def test_matches_on_logitech_company_id(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=_mfr(_cpp_payload()))
        assert len(registry.match(ad)) == 1

    def test_matches_full_128bit_uuid_form(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=["0000fe61-0000-1000-8000-00805f9b34fb"])
        assert len(registry.match(ad)) == 1

    def test_does_not_match_other_vendor(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=b"\x4c\x00\x01\x02", service_uuids=["feed"])
        assert registry.match(ad) == []


class TestUEBoomCppDecode:
    def _parse(self, **kw):
        parser = UEBoomParser()
        ad = _make_ad(
            manufacturer_data=_mfr(_cpp_payload(**kw)),
            service_uuids=[UE_SERVICE_UUID],
        )
        return parser.parse(ad)

    def test_returns_result(self):
        res = self._parse()
        assert res is not None
        assert res.parser_name == "ue_boom"
        assert res.beacon_type == "ue_boom"
        assert res.device_class == "audio"
        assert res.metadata["vendor"] == "Ultimate Ears (Logitech)"
        assert res.metadata["ad_format"] == "cpp_legacy"

    def test_battery_and_power(self):
        res = self._parse(battery=85, powered=True)
        assert res.metadata["battery_percent"] == 85
        assert res.metadata["is_powered"] is True

    def test_powered_off_clears_bit7(self):
        res = self._parse(battery=42, powered=False)
        assert res.metadata["battery_percent"] == 42
        assert res.metadata["is_powered"] is False

    def test_battery_over_100_is_rejected(self):
        # 0x7F = 127% -> not a plausible battery, no decode
        parser = UEBoomParser()
        ad = _make_ad(manufacturer_data=_mfr(bytes([0x7F]) + bytes(12)))
        assert parser.parse(ad) is None

    def test_volume(self):
        res = self._parse(volume=0x2B)
        assert res.metadata["volume"] == 0x2B

    def test_status_byte_bits(self):
        # 0xD4 = powered | bt-classic | streaming=2 | broadcasting
        res = self._parse(status=0xD4)
        assert res.metadata["bt_classic_connected"] is True
        assert res.metadata["internet_connected"] is False
        assert res.metadata["streaming_status"] == 2
        assert res.metadata["is_broadcasting"] is True
        assert res.metadata["is_button_pressed"] is False

    def test_status_byte_button_and_internet(self):
        res = self._parse(status=0x21)
        assert res.metadata["internet_connected"] is True
        assert res.metadata["is_button_pressed"] is True
        assert res.metadata["is_broadcasting"] is False
        assert res.metadata["streaming_status"] == 0

    def test_extra_flags_byte(self):
        # 0x7A = broadcast_status 3 | connect_button | autoconnect | audio_config 2
        res = self._parse(extra=0x7A)
        assert res.metadata["broadcast_status"] == 3
        assert res.metadata["broadcast_status_name"] == "STREAMING_A2DP"
        assert res.metadata["connect_button"] is True
        assert res.metadata["autoconnect"] is True
        assert res.metadata["broadcast_known"] is False
        assert res.metadata["audio_config"] == 2

    def test_broadcast_status_power_off(self):
        res = self._parse(extra=0x00)
        assert res.metadata["broadcast_status"] == 0
        assert res.metadata["broadcast_status_name"] == "POWER_OFF"

    def test_broadcast_mac(self):
        res = self._parse(broadcast_mac=b"\xde\xad\xbe\xef\x00\x11")
        assert res.metadata["broadcast_mac"] == "de:ad:be:ef:00:11"

    def test_broadcast_mac_all_zero_is_omitted(self):
        res = self._parse(broadcast_mac=b"\x00" * 6)
        assert "broadcast_mac" not in res.metadata

    def test_name_revision_nibble(self):
        res = self._parse(tail=0xA5)
        assert res.metadata["name_revision"] == 5

    def test_raw_payload_hex_is_full_manufacturer_data(self):
        parser = UEBoomParser()
        mfr = _mfr(_cpp_payload())
        ad = _make_ad(manufacturer_data=mfr, service_uuids=[UE_SERVICE_UUID])
        res = parser.parse(ad)
        assert res.raw_payload_hex == mfr.hex()

    def test_service_uuid_flag_recorded(self):
        parser = UEBoomParser()
        ad = _make_ad(manufacturer_data=_mfr(_cpp_payload()))
        res = parser.parse(ad)
        assert res.metadata["ue_service_uuid"] is False


class TestUEBoomWaspDecode:
    def _parse(self, status=0xC5):
        parser = UEBoomParser()
        ad = _make_ad(
            manufacturer_data=_mfr(_wasp_payload(status=status)),
            service_uuids=[UE_SERVICE_UUID],
        )
        return parser.parse(ad)

    def test_format_detected(self):
        res = self._parse()
        assert res.metadata["ad_format"] == "wasp"
        assert res.metadata["pid"] == 0x030D
        assert res.metadata["model"] == "WASP"

    def test_status_bits(self):
        # 0xC5 = audio-source | playing-audio | powered | group 1
        res = self._parse(status=0xC5)
        assert res.metadata["is_audio_source"] is True
        assert res.metadata["is_playing_audio"] is True
        assert res.metadata["is_playing_local_audio"] is False
        assert res.metadata["is_playing_streaming_audio"] is False
        assert res.metadata["is_powered"] is True
        assert res.metadata["group_id"] == 1

    def test_streaming_and_local_audio(self):
        # 0x30 = playing-local | playing-streaming
        res = self._parse(status=0x30)
        assert res.metadata["is_playing_local_audio"] is True
        assert res.metadata["is_playing_streaming_audio"] is True
        assert res.metadata["is_powered"] is False
        assert res.metadata["group_id"] == 0

    def test_wasp_has_no_battery_field(self):
        res = self._parse()
        assert "battery_percent" not in res.metadata


class TestUEBoomPresenceOnly:
    def test_uuid_only_presence(self):
        parser = UEBoomParser()
        ad = _make_ad(service_uuids=[UE_SERVICE_UUID], local_name="UE BOOM 3")
        res = parser.parse(ad)
        assert res is not None
        assert res.metadata["ad_format"] == "presence"
        assert res.metadata["device_name"] == "UE BOOM 3"
        assert "battery_percent" not in res.metadata

    def test_bare_logitech_cid_without_uuid_is_ignored(self):
        # A Logitech mouse/keyboard: right CID, no FE61, short payload.
        parser = UEBoomParser()
        ad = _make_ad(manufacturer_data=_mfr(b"\x01\x02\x03"))
        assert parser.parse(ad) is None

    def test_wrong_company_id_without_uuid_is_ignored(self):
        parser = UEBoomParser()
        ad = _make_ad(manufacturer_data=b"\x4c\x00" + _cpp_payload())
        assert parser.parse(ad) is None

    def test_no_data_at_all(self):
        parser = UEBoomParser()
        assert parser.parse(_make_ad()) is None


class TestUEBoomIdentity:
    def test_identity_hash_from_mac(self):
        parser = UEBoomParser()
        ad = _make_ad(
            manufacturer_data=_mfr(_cpp_payload()),
            service_uuids=[UE_SERVICE_UUID],
        )
        res = parser.parse(ad)
        expected = hashlib.sha256(b"ueboom:AA:BB:CC:DD:EE:FF").hexdigest()[:16]
        assert res.identifier_hash == expected
        assert len(res.identifier_hash) == 16

    def test_identity_is_stable_across_state_change(self):
        parser = UEBoomParser()
        a = parser.parse(
            _make_ad(
                manufacturer_data=_mfr(_cpp_payload(battery=90, volume=1)),
                service_uuids=[UE_SERVICE_UUID],
            )
        )
        b = parser.parse(
            _make_ad(
                manufacturer_data=_mfr(_cpp_payload(battery=20, volume=30)),
                service_uuids=[UE_SERVICE_UUID],
            )
        )
        assert a.identifier_hash == b.identifier_hash

    def test_storage_schema_is_none(self):
        assert UEBoomParser().storage_schema() is None


class TestUEBoomTruncated:
    @pytest.mark.parametrize("n", [0, 1, 5, 12])
    def test_short_payload_falls_back_to_presence(self, n):
        parser = UEBoomParser()
        ad = _make_ad(
            manufacturer_data=_mfr(bytes(n)),
            service_uuids=[UE_SERVICE_UUID],
        )
        res = parser.parse(ad)
        assert res is not None
        assert res.metadata["ad_format"] == "presence"
