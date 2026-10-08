"""Tests for Shelly BLU sensor BLE advertisement plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.shelly_blu import ShellyBluParser, SHELLY_COMPANY_ID


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
        name="shelly_blu",
        company_id=SHELLY_COMPANY_ID,
        local_name_pattern=r"^SB[A-Z]{2}-",
        description="Shelly BLU sensor advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(ShellyBluParser):
        pass

    return registry


def _shelly_mfr_data(flags=0x0003, model_id=0x1001, mac="3C:2E:F5:00:00:01", extra=b""):
    """Build Shelly (CID 0x0BA9) mfr data per shelly-smartcontrol report
    (BleDevice.parseManufacturerData, BleDevice.java:973-1034):
    CID LE | 0x01 flags(u16 LE) | 0x0B model(u16 LE) | 0x0A mac(6, reversed)."""
    payload = b""
    if flags is not None:
        payload += b"\x01" + flags.to_bytes(2, "little")
    if model_id is not None:
        payload += b"\x0b" + model_id.to_bytes(2, "little")
    if mac is not None:
        payload += b"\x0a" + bytes.fromhex(mac.replace(":", ""))[::-1]
    return SHELLY_COMPANY_ID.to_bytes(2, "little") + payload + extra


class TestShellyBluParser:
    # --- Registry matching ---

    def test_matches_company_id_0x0BA9(self):
        """Matches on Shelly company_id 0x0BA9."""
        registry = _make_registry()
        ad = _make_ad(manufacturer_data=_shelly_mfr_data())
        matches = registry.match(ad)
        assert len(matches) >= 1

    def test_matches_local_name_pattern(self):
        """Matches on local_name 'SBBT-002C' via name pattern."""
        registry = _make_registry()
        ad = _make_ad(
            manufacturer_data=_shelly_mfr_data(),
            local_name="SBBT-002C",
        )
        matches = registry.match(ad)
        assert len(matches) >= 1

    # --- Basic fields ---

    def test_parser_name(self):
        """parser_name is 'shelly_blu'."""
        parser = ShellyBluParser()
        ad = _make_ad(manufacturer_data=_shelly_mfr_data())
        result = parser.parse(ad)
        assert result.parser_name == "shelly_blu"

    def test_beacon_type(self):
        """beacon_type is 'shelly_blu'."""
        parser = ShellyBluParser()
        ad = _make_ad(manufacturer_data=_shelly_mfr_data())
        result = parser.parse(ad)
        assert result.beacon_type == "shelly_blu"

    # --- Manufacturer data parsing ---

    # --- Device model from local_name ---

    def test_model_blu_button(self):
        """'SBBT-002C' -> model='BLU Button'."""
        parser = ShellyBluParser()
        ad = _make_ad(
            manufacturer_data=_shelly_mfr_data(),
            local_name="SBBT-002C",
        )
        result = parser.parse(ad)
        assert result.metadata["model"] == "BLU Button"

    def test_model_blu_door_window(self):
        """'SBDW-002C' -> model='BLU Door/Window'."""
        parser = ShellyBluParser()
        ad = _make_ad(
            manufacturer_data=_shelly_mfr_data(),
            local_name="SBDW-002C",
        )
        result = parser.parse(ad)
        assert result.metadata["model"] == "BLU Door/Window"

    def test_model_blu_motion(self):
        """'SBMO-003Z' -> model='BLU Motion'."""
        parser = ShellyBluParser()
        ad = _make_ad(
            manufacturer_data=_shelly_mfr_data(),
            local_name="SBMO-003Z",
        )
        result = parser.parse(ad)
        assert result.metadata["model"] == "BLU Motion"

    def test_model_blu_ht(self):
        """'SBHT-003C' -> model='BLU H&T'."""
        parser = ShellyBluParser()
        ad = _make_ad(
            manufacturer_data=_shelly_mfr_data(),
            local_name="SBHT-003C",
        )
        result = parser.parse(ad)
        assert result.metadata["model"] == "BLU H&T"

    def test_model_unknown_prefix(self):
        """'SBXX-001A' -> model='BLU Unknown'."""
        parser = ShellyBluParser()
        ad = _make_ad(
            manufacturer_data=_shelly_mfr_data(),
            local_name="SBXX-001A",
        )
        result = parser.parse(ad)
        assert result.metadata["model"] == "BLU Unknown"

    def test_model_no_local_name(self):
        """None local_name -> model='Unknown'."""
        parser = ShellyBluParser()
        ad = _make_ad(manufacturer_data=_shelly_mfr_data())
        result = parser.parse(ad)
        assert result.metadata["model"] == "Unknown"

    # --- local_name in metadata ---

    def test_local_name_in_metadata(self):
        """metadata['local_name'] is set to raw local_name value."""
        parser = ShellyBluParser()
        ad = _make_ad(
            manufacturer_data=_shelly_mfr_data(),
            local_name="SBBT-002C",
        )
        result = parser.parse(ad)
        assert result.metadata["local_name"] == "SBBT-002C"

    def test_local_name_none_in_metadata(self):
        """metadata['local_name'] is None when local_name not set."""
        parser = ShellyBluParser()
        ad = _make_ad(manufacturer_data=_shelly_mfr_data())
        result = parser.parse(ad)
        assert result.metadata["local_name"] is None

    # --- Identity hash ---

    # --- raw_payload_hex ---

    # --- Edge cases ---

    def test_returns_none_wrong_company_id(self):
        """Returns None when company_id is not Shelly."""
        parser = ShellyBluParser()
        data = (0x004C).to_bytes(2, "little") + b"\x01\x02\x03"
        ad = _make_ad(manufacturer_data=data)
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_no_manufacturer_data(self):
        """Returns None when manufacturer_data is None."""
        parser = ShellyBluParser()
        ad = _make_ad()
        result = parser.parse(ad)
        assert result is None


class TestShellyReportMfrDecode:
    """Report-cited layout replaces the old fictional
    device_type/packet_counter/battery decode (no such bytes exist; BLU
    telemetry rides in BTHome 0xFCD2 service data, handled by bthome.py)."""

    def test_full_advert_offsets(self):
        mfr = bytes.fromhex("a90b" "011300" "0b0110" "0a010000f52e3c")
        r = ShellyBluParser().parse(_make_ad(manufacturer_data=mfr))
        md = r.metadata
        assert md["flags"] == 0x0013
        assert md["discoverable"] is True
        assert md["auth_enabled"] is True
        assert md["rpc_enabled"] is False
        assert md["buzzer_enabled"] is False
        assert md["pairing_mode"] is True
        assert md["provision_locked"] is False
        assert md["model_id"] == 0x1001
        assert md["device_mac"] == "3C:2E:F5:00:00:01"
        assert r.raw_payload_hex == mfr[2:].hex()

    def test_flags_block_optional(self):
        r = ShellyBluParser().parse(_make_ad(manufacturer_data=_shelly_mfr_data(flags=None)))
        assert "flags" not in r.metadata
        assert r.metadata["model_id"] == 0x1001

    def test_jti_object(self):
        mfr = _shelly_mfr_data(mac=None, extra=bytes.fromhex("09a1b2c3d4e5f6"))
        r = ShellyBluParser().parse(_make_ad(manufacturer_data=mfr))
        assert r.metadata["jti"] == "a1b2c3d4e5f6"

    def test_identity_from_advertised_device_mac(self):
        p = ShellyBluParser()
        a = p.parse(_make_ad(manufacturer_data=_shelly_mfr_data(), mac_address="11:11:11:11:11:11"))
        b = p.parse(_make_ad(manufacturer_data=_shelly_mfr_data(), mac_address="22:22:22:22:22:22"))
        assert a.identifier_hash == b.identifier_hash
        assert a.identifier_hash == hashlib.sha256(b"shelly:3C:2E:F5:00:00:01").hexdigest()[:16]

    def test_identity_falls_back_to_mac(self):
        mac = "11:22:33:44:55:66"
        r = ShellyBluParser().parse(_make_ad(manufacturer_data=_shelly_mfr_data(mac=None), mac_address=mac))
        assert r.identifier_hash == hashlib.sha256(f"{mac}:shelly_blu".encode()).hexdigest()[:16]

    def test_truncated_tlv_does_not_crash(self):
        mfr = SHELLY_COMPANY_ID.to_bytes(2, "little") + b"\x01\x03\x00\x0a\x01\x02"
        r = ShellyBluParser().parse(_make_ad(manufacturer_data=mfr))
        assert r is not None
        assert "device_mac" not in r.metadata
        assert r.metadata["flags"] == 3

    def test_cid_only_returns_none(self):
        assert ShellyBluParser().parse(_make_ad(manufacturer_data=b"\xa9\x0b")) is None

    def test_device_class(self):
        p = ShellyBluParser()
        assert p.parse(_make_ad(manufacturer_data=_shelly_mfr_data(), local_name="SBBT-002C")).device_class == "sensor"
        assert p.parse(_make_ad(manufacturer_data=_shelly_mfr_data())).device_class == "smart_home"

    def test_bthome_encryption_flag_surfaced(self):
        """bthome.py drops encrypted frames; surface the bit here (BleDevice.java:888)."""
        p = ShellyBluParser()
        r = p.parse(_make_ad(manufacturer_data=_shelly_mfr_data(),
                             service_data={"fcd2": bytes.fromhex("45aabbccdd")}))
        assert r.metadata["bthome_encrypted"] is True
        r = p.parse(_make_ad(manufacturer_data=_shelly_mfr_data(),
                             service_data={"fcd2": bytes.fromhex("44000164")}))
        assert r.metadata["bthome_encrypted"] is False

    def test_does_not_claim_bthome_service_uuid(self):
        """Service-data-only BLU adverts belong to bthome.py, not shelly_blu."""
        import adwatch.plugins.shelly_blu  # noqa: F401
        from adwatch.registry import _default_registry
        entry = next(e for e in _default_registry._parsers if e["name"] == "shelly_blu")
        ad = _make_ad(service_data={"fcd2": bytes.fromhex("44000164")})
        assert not _default_registry._entry_matches(entry, ad)
