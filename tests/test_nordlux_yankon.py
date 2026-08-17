"""Tests for the Nordlux / Yankon proprietary mesh beacon plugin.

Byte layout per apk-ble-hunting/reports/nordlux-smartlight_passive.md
(`DeviceDescriptionUtil.java:56-324`). Offsets in that report are relative
to the manufacturer payload *after* the 2-byte company ID, i.e. exactly
``RawAdvertisement.manufacturer_payload`` -- no offset shift needed.
"""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.nordlux_yankon import (
    NordluxYankonParser,
    YANKON_COMPANY_ID,
    YANKON_PAYLOAD_LEN,
    checksum,
)


def _make_ad(**kwargs):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "public",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _build_payload(beacon=b"2000", unknown=0x00, chip=0x0D, major=0x03,
                   net_key=b"\x01\x00", app_key=b"\x02\x00",
                   dev_id=b"\x11\x22\x33\x44\x55\x66",
                   unicast=b"\x05\x01", minor=0x07, uv_group=0x02,
                   spare=0x00, room=0x09, bad_checksum=False):
    body = (beacon + bytes([unknown, chip, major]) + net_key + app_key
            + dev_id + unicast + bytes([minor, uv_group, spare, room]))
    assert len(body) == YANKON_PAYLOAD_LEN - 1, len(body)
    ck = checksum(body)
    if bad_checksum:
        ck = (ck + 1) & 0xFF
    return body + bytes([ck])


def _mfr(payload):
    return struct.pack("<H", YANKON_COMPANY_ID) + payload


def _registry():
    registry = ParserRegistry()

    @register_parser(
        name="nordlux_yankon",
        company_id=YANKON_COMPANY_ID,
        description="Nordlux Yankon",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(NordluxYankonParser):
        pass

    return registry


class TestYankonConstants:
    def test_company_id(self):
        assert YANKON_COMPANY_ID == 0x6E78

    def test_wire_bytes_are_little_endian(self):
        """Report cites the on-air bytes as `78 6E`."""
        assert struct.pack("<H", YANKON_COMPANY_ID) == b"\x78\x6e"

    def test_payload_length(self):
        assert YANKON_PAYLOAD_LEN == 24

    def test_checksum_is_low_byte_of_sum(self):
        assert checksum(b"\x01\x02\x03") == 6
        assert checksum(b"\xff\xff") == 0xFE


class TestYankonMatching:
    def test_matches_company_id(self):
        ad = _make_ad(manufacturer_data=_mfr(_build_payload()))
        assert len(_registry().match(ad)) == 1

    def test_does_not_match_other_company_id(self):
        ad = _make_ad(manufacturer_data=struct.pack("<H", 0x004C) + _build_payload())
        assert _registry().match(ad) == []

    def test_rejects_bad_checksum(self):
        """checkDeviceIsYankon() gates on the byte-23 checksum."""
        ad = _make_ad(manufacturer_data=_mfr(_build_payload(bad_checksum=True)))
        assert NordluxYankonParser().parse(ad) is None

    def test_rejects_short_payload(self):
        ad = _make_ad(manufacturer_data=_mfr(_build_payload()[:20]))
        assert NordluxYankonParser().parse(ad) is None

    def test_rejects_missing_manufacturer_data(self):
        assert NordluxYankonParser().parse(_make_ad()) is None


class TestYankonDecode:
    @pytest.fixture
    def result(self):
        ad = _make_ad(manufacturer_data=_mfr(_build_payload()))
        return NordluxYankonParser().parse(ad)

    def test_parses(self, result):
        assert result is not None
        assert result.parser_name == "nordlux_yankon"
        assert result.beacon_type == "nordlux_yankon"
        assert result.device_class == "smart_light"

    def test_beacon_type_is_reversed_ascii(self, result):
        assert result.metadata["beacon_type"] == "0002"

    def test_model_lookup(self, result):
        assert result.metadata["model"] == "A60 bulb"

    def test_unknown_model_has_no_label(self):
        ad = _make_ad(manufacturer_data=_mfr(_build_payload(beacon=b"9999")))
        result = NordluxYankonParser().parse(ad)
        assert result.metadata["beacon_type"] == "9999"
        assert "model" not in result.metadata

    def test_chip_and_versions(self, result):
        assert result.metadata["chip_type"] == 0x0D
        assert result.metadata["firmware_major"] == 3
        assert result.metadata["firmware_minor"] == 7

    def test_key_indices(self, result):
        assert result.metadata["spec_net_key_index"] == 1
        assert result.metadata["spec_app_key_index"] == 2

    def test_provisioned_when_both_keys_set(self, result):
        assert result.metadata["provisioned"] is True

    def test_unprovisioned_when_net_key_zero(self):
        ad = _make_ad(manufacturer_data=_mfr(_build_payload(net_key=b"\x00\x00")))
        result = NordluxYankonParser().parse(ad)
        assert result.metadata["provisioned"] is False

    def test_unprovisioned_when_app_key_zero(self):
        ad = _make_ad(manufacturer_data=_mfr(_build_payload(app_key=b"\x00\x00")))
        result = NordluxYankonParser().parse(ad)
        assert result.metadata["provisioned"] is False

    def test_device_id_reversed(self, result):
        assert result.metadata["device_id"] == "665544332211"

    def test_mesh_unicast_address(self, result):
        assert result.metadata["mesh_unicast_address"] == 0x0105

    def test_group_and_room(self, result):
        assert result.metadata["uv_group"] == 2
        assert result.metadata["room"] == 9

    def test_checksum_recorded(self, result):
        assert result.metadata["checksum_valid"] is True

    def test_raw_payload_hex(self):
        payload = _build_payload()
        ad = _make_ad(manufacturer_data=_mfr(payload))
        result = NordluxYankonParser().parse(ad)
        assert result.raw_payload_hex == payload.hex()


class TestYankonMeshBeaconContext:
    def test_flags_unprovisioned_sig_beacon(self):
        ad = _make_ad(manufacturer_data=_mfr(_build_payload()),
                      service_uuids=["00001827-0000-1000-8000-00805f9b34fb"])
        result = NordluxYankonParser().parse(ad)
        assert result.metadata["mesh_provisioning_beacon"] is True

    def test_flags_proxy_beacon(self):
        ad = _make_ad(manufacturer_data=_mfr(_build_payload()),
                      service_uuids=["00001828-0000-1000-8000-00805f9b34fb"])
        result = NordluxYankonParser().parse(ad)
        assert result.metadata["mesh_proxy_beacon"] is True

    def test_no_mesh_flags_by_default(self):
        ad = _make_ad(manufacturer_data=_mfr(_build_payload()))
        result = NordluxYankonParser().parse(ad)
        assert "mesh_provisioning_beacon" not in result.metadata
        assert "mesh_proxy_beacon" not in result.metadata


class TestYankonIdentity:
    def test_identity_from_device_id(self):
        ad = _make_ad(manufacturer_data=_mfr(_build_payload()))
        result = NordluxYankonParser().parse(ad)
        expected = hashlib.sha256(b"nordlux_yankon:665544332211").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_stable_across_mac(self):
        payload = _build_payload()
        a = NordluxYankonParser().parse(
            _make_ad(manufacturer_data=_mfr(payload), mac_address="AA:BB:CC:DD:EE:FF"))
        b = NordluxYankonParser().parse(
            _make_ad(manufacturer_data=_mfr(payload), mac_address="11:22:33:44:55:66"))
        assert a.identifier_hash == b.identifier_hash

    def test_identity_differs_per_device(self):
        a = NordluxYankonParser().parse(_make_ad(manufacturer_data=_mfr(_build_payload())))
        b = NordluxYankonParser().parse(_make_ad(
            manufacturer_data=_mfr(_build_payload(dev_id=b"\xaa\xbb\xcc\xdd\xee\xff"))))
        assert a.identifier_hash != b.identifier_hash

    def test_identity_hash_length(self):
        result = NordluxYankonParser().parse(_make_ad(manufacturer_data=_mfr(_build_payload())))
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_stable_key_excludes_volatile_state(self):
        result = NordluxYankonParser().parse(_make_ad(manufacturer_data=_mfr(_build_payload())))
        assert result.stable_key == "nordlux_yankon:665544332211"
