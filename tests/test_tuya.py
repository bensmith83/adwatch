"""Tests for Tuya / Smart Life BLE advertisement plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.tuya import TuyaParser, TUYA_COMPANY_ID


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
        name="tuya",
        company_id=TUYA_COMPANY_ID,
        description="Tuya / Smart Life BLE advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(TuyaParser):
        pass

    return registry


def _tuya_mfr_data(protocol_version=0x03, flags=0x00, product_id=b""):
    """Build manufacturer data: company_id (LE) + protocol_version + flags + product_id."""
    payload = bytes([protocol_version, flags]) + product_id
    return TUYA_COMPANY_ID.to_bytes(2, "little") + payload


class TestTuyaParser:
    # --- Registry matching ---

    def test_matches_company_id_0x07D0(self):
        """Matches on Tuya company_id 0x07D0."""
        registry = _make_registry()
        ad = _make_ad(manufacturer_data=_tuya_mfr_data())
        matches = registry.match(ad)
        assert len(matches) >= 1

    # --- Basic fields ---

    def test_parser_name(self):
        """parser_name is 'tuya'."""
        parser = TuyaParser()
        ad = _make_ad(manufacturer_data=_tuya_mfr_data())
        result = parser.parse(ad)
        assert result.parser_name == "tuya"

    def test_beacon_type(self):
        """beacon_type is 'tuya'."""
        parser = TuyaParser()
        ad = _make_ad(manufacturer_data=_tuya_mfr_data())
        result = parser.parse(ad)
        assert result.beacon_type == "tuya"

    def test_device_class_smart_home(self):
        """device_class is 'smart_home'."""
        parser = TuyaParser()
        ad = _make_ad(manufacturer_data=_tuya_mfr_data())
        result = parser.parse(ad)
        assert result.device_class == "smart_home"

    # --- Manufacturer data parsing ---

    def test_protocol_version_from_payload(self):
        """metadata['protocol_version'] is byte 0 of payload."""
        parser = TuyaParser()
        ad = _make_ad(manufacturer_data=_tuya_mfr_data(protocol_version=0x05))
        result = parser.parse(ad)
        assert result.metadata["protocol_version"] == 0x05

    def test_flags_from_payload(self):
        """metadata['flags'] is byte 1 of payload."""
        parser = TuyaParser()
        ad = _make_ad(manufacturer_data=_tuya_mfr_data(flags=0x42))
        result = parser.parse(ad)
        assert result.metadata["flags"] == 0x42

    # --- Pairing flag detection ---

    def test_pairing_true_when_flag_bit0_set(self):
        """flags=0x01 -> metadata['pairing'] = True."""
        parser = TuyaParser()
        ad = _make_ad(manufacturer_data=_tuya_mfr_data(flags=0x01))
        result = parser.parse(ad)
        assert result.metadata["pairing"] is True

    def test_pairing_false_when_flag_bit0_clear(self):
        """flags=0x00 -> metadata['pairing'] = False."""
        parser = TuyaParser()
        ad = _make_ad(manufacturer_data=_tuya_mfr_data(flags=0x00))
        result = parser.parse(ad)
        assert result.metadata["pairing"] is False

    def test_pairing_true_when_flag_bit0_set_with_other_bits(self):
        """flags=0x03 (bit 0 set) -> metadata['pairing'] = True."""
        parser = TuyaParser()
        ad = _make_ad(manufacturer_data=_tuya_mfr_data(flags=0x03))
        result = parser.parse(ad)
        assert result.metadata["pairing"] is True

    # --- Product ID ---

    def test_product_id_hex_present(self):
        """product_id=b'\\xAB\\xCD\\xEF' -> metadata['product_id_hex'] = 'abcdef'."""
        parser = TuyaParser()
        ad = _make_ad(manufacturer_data=_tuya_mfr_data(product_id=b"\xAB\xCD\xEF"))
        result = parser.parse(ad)
        assert result.metadata["product_id_hex"] == "abcdef"

    def test_product_id_hex_absent_when_no_extra_bytes(self):
        """No product_id bytes (just 2-byte payload) -> 'product_id_hex' not in metadata."""
        parser = TuyaParser()
        ad = _make_ad(manufacturer_data=_tuya_mfr_data(product_id=b""))
        result = parser.parse(ad)
        assert "product_id_hex" not in result.metadata

    # --- Local name in metadata ---

    def test_local_name_in_metadata(self):
        """metadata['local_name'] is set to raw local_name value."""
        parser = TuyaParser()
        ad = _make_ad(
            manufacturer_data=_tuya_mfr_data(),
            local_name="TY-SmartPlug",
        )
        result = parser.parse(ad)
        assert result.metadata["local_name"] == "TY-SmartPlug"

    # --- Identity hash ---

    def test_identity_hash(self):
        """Identity hash is SHA256(mac_address:tuya)[:16]."""
        mac = "11:22:33:44:55:66"
        parser = TuyaParser()
        ad = _make_ad(manufacturer_data=_tuya_mfr_data(), mac_address=mac)
        result = parser.parse(ad)
        expected = hashlib.sha256(f"{mac}:tuya".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    # --- raw_payload_hex ---

    def test_raw_payload_hex(self):
        """raw_payload_hex contains hex of manufacturer payload (without company_id)."""
        parser = TuyaParser()
        payload_bytes = bytes([0x03, 0x00]) + b"\xAB\xCD"
        ad = _make_ad(manufacturer_data=TUYA_COMPANY_ID.to_bytes(2, "little") + payload_bytes)
        result = parser.parse(ad)
        assert result.raw_payload_hex == payload_bytes.hex()

    # --- Edge cases ---

    def test_returns_none_wrong_company_id(self):
        """Returns None when company_id is not Tuya."""
        parser = TuyaParser()
        data = (0x004C).to_bytes(2, "little") + b"\x01\x02\x03"
        ad = _make_ad(manufacturer_data=data)
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_no_manufacturer_data(self):
        """Returns None when manufacturer_data is None."""
        parser = TuyaParser()
        ad = _make_ad()
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_short_payload(self):
        """Returns None when payload < 2 bytes (company_id + 1 byte only)."""
        parser = TuyaParser()
        ad = _make_ad(manufacturer_data=TUYA_COMPANY_ID.to_bytes(2, "little") + b"\x01")
        result = parser.parse(ad)
        assert result is None

    def test_handles_local_name_none(self):
        """Parses successfully with local_name=None."""
        parser = TuyaParser()
        ad = _make_ad(manufacturer_data=_tuya_mfr_data())
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "tuya"
        assert "local_name" not in result.metadata or result.metadata.get("local_name") is None


class TestTuyaFlowerCareFD50:
    """Tuya "pink" FlowerCare clone — service data 0xFD50, fixed 9 bytes.

    Ground truth: reports/watchflower_passive.md (WatchFlower is open source;
    src/src/devices/device_flowercare_tuya.cpp:120-179).  Temperature and soil
    conductivity are stored **big-endian**, which is unusual for BLE.
    """

    @staticmethod
    def _payload(moisture=42, temp_raw=235, lux=1500, battery=88, cond=350):
        return (
            bytes([moisture])
            + temp_raw.to_bytes(2, "big", signed=True)
            + lux.to_bytes(3, "little")
            + bytes([battery])
            + cond.to_bytes(2, "big")
        )

    def _parse(self, payload, uuid="fd50", **adkw):
        ad = _make_ad(service_data={uuid: payload}, **adkw)
        return TuyaParser().parse(ad)

    def test_full_nine_byte_frame(self):
        result = self._parse(self._payload())
        assert result is not None
        assert result.parser_name == "tuya"
        assert result.beacon_type == "tuya_flowercare"
        assert result.device_class == "sensor"
        assert result.metadata["soil_moisture"] == 42
        assert result.metadata["temperature_c"] == 23.5
        assert result.metadata["luminosity"] == 1500
        assert result.metadata["battery"] == 88
        assert result.metadata["soil_conductivity"] == 350

    def test_temperature_is_big_endian(self):
        """`data[2] + (data[1] << 8)` — MSB first, unlike the rest of BLE."""
        # 0x00 0xEB big-endian = 235 → 23.5 C.  Little-endian would be 60160.
        payload = bytes([10]) + bytes([0x00, 0xEB]) + b"\x00\x00\x00" + bytes([50]) + b"\x00\x00"
        result = self._parse(payload)
        assert result.metadata["temperature_c"] == 23.5

    def test_negative_temperature(self):
        result = self._parse(self._payload(temp_raw=-55))
        assert result.metadata["temperature_c"] == -5.5

    def test_conductivity_is_big_endian(self):
        """`data[8] + (data[7] << 8)`."""
        payload = bytes([10]) + b"\x00\x00" + b"\x00\x00\x00" + bytes([50]) + bytes([0x01, 0x2C])
        assert self._parse(payload).metadata["soil_conductivity"] == 300

    def test_luminosity_is_little_endian_24bit(self):
        payload = bytes([10]) + b"\x00\x00" + bytes([0x40, 0x0D, 0x03]) + bytes([50]) + b"\x00\x00"
        assert self._parse(payload).metadata["luminosity"] == 0x030D40

    def test_wrong_length_rejected(self):
        """WatchFlower requires exactly 9 bytes."""
        assert self._parse(self._payload()[:8]) is None
        assert self._parse(self._payload() + b"\x00") is None

    def test_full_128bit_uuid_form_accepted(self):
        result = self._parse(
            self._payload(), uuid="0000fd50-0000-1000-8000-00805f9b34fb"
        )
        assert result is not None
        assert result.metadata["soil_moisture"] == 42

    def test_identity_hash_uses_mac(self):
        result = self._parse(self._payload(), mac_address="11:22:33:44:55:66")
        assert result.identifier_hash == hashlib.sha256(
            b"11:22:33:44:55:66:tuya"
        ).hexdigest()[:16]

    def test_raw_payload_hex(self):
        payload = self._payload()
        assert self._parse(payload).raw_payload_hex == payload.hex()

    def test_registry_matches_fd50_service_data(self):
        from adwatch.plugins.tuya import TUYA_FLOWERCARE_UUID

        registry = ParserRegistry()

        @register_parser(
            name="tuya", company_id=TUYA_COMPANY_ID,
            service_uuid=TUYA_FLOWERCARE_UUID,
            local_name_pattern=r"^(Smart\.[A-Z0-9]{2}\.WIFI|TY)$",
            description="Tuya", version="1.0.0", core=False, registry=registry,
        )
        class _P(TuyaParser):
            pass

        ad = _make_ad(service_data={"fd50": self._payload()})
        assert len(registry.match(ad)) == 1

    def test_registry_matches_ty_name(self):
        """WatchFlower discovers the Tuya plant sensor by the exact name `TY`."""
        registry = ParserRegistry()

        @register_parser(
            name="tuya", company_id=TUYA_COMPANY_ID,
            service_uuid="fd50",
            local_name_pattern=r"^(Smart\.[A-Z0-9]{2}\.WIFI|TY)$",
            description="Tuya", version="1.0.0", core=False, registry=registry,
        )
        class _P(TuyaParser):
            pass

        assert len(registry.match(_make_ad(local_name="TY"))) == 1
        assert registry.match(_make_ad(local_name="TYPE-C")) == []

    def test_manufacturer_path_still_wins_when_both_present(self):
        """A Tuya CID advert with FD50 service data keeps the CID decode."""
        ad = _make_ad(
            manufacturer_data=_tuya_mfr_data(protocol_version=0x03, flags=0x01),
            service_data={"fd50": self._payload()},
        )
        result = TuyaParser().parse(ad)
        assert result.beacon_type == "tuya"
        assert result.metadata["protocol_version"] == 0x03
