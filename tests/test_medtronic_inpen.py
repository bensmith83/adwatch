"""Tests for the Medtronic / Companion InPen smart insulin pen plugin.

Per apk-ble-hunting/reports/companionmedical-inpen_passive.md:
  - Discovery filter is the 16-bit service UUID 0xBFD0.
  - The app reads absolute scan-record offsets 10..13 out of the advertisement:
    offset 10 = alert/status flag byte, offsets 11-13 = 3-byte pen ID stored
    little-endian and rendered big-endian ("%02x%02x%02x" of bytes 13,12,11).
  - Offsets 10..13 land in the *value* of the AD element that follows the
    flags + 16-bit-UUID structures, so value[0] = flags and value[1:4] = pen ID.
"""

import hashlib

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.medtronic_inpen import (
    INPEN_SERVICE_UUID,
    INPEN_SERVICE_UUID_FULL,
    MedtronicInPenParser,
)


@pytest.fixture
def parser():
    return MedtronicInPenParser()


def make_raw(**kwargs):
    defaults = dict(
        timestamp="2026-08-16T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        manufacturer_data=None,
        service_data=None,
        service_uuids=[],
        local_name=None,
        rssi=-60,
    )
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(
        name="medtronic_inpen",
        service_uuid=INPEN_SERVICE_UUID,
        description="InPen",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(MedtronicInPenParser):
        pass

    return _P


class TestConstants:
    def test_service_uuid_is_bfd0(self):
        assert INPEN_SERVICE_UUID == "bfd0"
        assert INPEN_SERVICE_UUID_FULL == "0000bfd0-0000-1000-8000-00805f9b34fb"


class TestMatching:
    def test_matches_short_service_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(make_raw(service_uuids=["bfd0"]))) == 1

    def test_matches_full_service_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(make_raw(service_uuids=[INPEN_SERVICE_UUID_FULL]))) == 1

    def test_matches_service_data_key(self):
        registry = ParserRegistry()
        _register(registry)
        raw = make_raw(service_data={"bfd0": bytes.fromhex("002c1b0a")})
        assert len(registry.match(raw)) == 1

    def test_does_not_match_other_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(make_raw(service_uuids=["fd6f"])) == []


class TestDecode:
    def test_pen_id_from_service_data_is_rendered_big_endian(self, parser):
        # record[10]=0x00 flags, record[11..13] = 2c 1b 0a -> display "0a1b2c"
        raw = make_raw(
            service_uuids=["bfd0"],
            service_data={"bfd0": bytes.fromhex("002c1b0a")},
        )
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["pen_id"] == "0a1b2c"
        assert result.metadata["alert_flags"] == 0x00
        assert result.metadata["payload_source"] == "service_data"

    def test_pen_id_from_manufacturer_payload(self, parser):
        # 2-byte CID then value: flags 0x04 + pen id LE 33 22 11 -> "112233"
        raw = make_raw(
            service_uuids=["bfd0"],
            manufacturer_data=bytes.fromhex("0701") + bytes.fromhex("04332211"),
        )
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["pen_id"] == "112233"
        assert result.metadata["alert_flags"] == 0x04
        assert result.metadata["payload_source"] == "manufacturer_data"

    def test_three_byte_value_is_pen_id_only(self, parser):
        raw = make_raw(
            service_uuids=["bfd0"],
            service_data={"bfd0": bytes.fromhex("2c1b0a")},
        )
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["pen_id"] == "0a1b2c"
        assert "alert_flags" not in result.metadata

    def test_alert_flag_set_is_reported(self, parser):
        raw = make_raw(
            service_uuids=["bfd0"],
            service_data={"bfd0": bytes.fromhex("0e2c1b0a")},
        )
        result = parser.parse(raw)
        assert result.metadata["alert_flags"] == 0x0E
        assert result.metadata["alert_flags_hex"] == "0e"

    def test_presence_only_without_payload(self, parser):
        result = parser.parse(make_raw(service_uuids=["bfd0"]))
        assert result is not None
        assert "pen_id" not in result.metadata
        assert result.metadata["product"] == "Medtronic InPen smart insulin pen"

    def test_device_class_and_names(self, parser):
        result = parser.parse(make_raw(service_uuids=["bfd0"], local_name="InPen"))
        assert result.parser_name == "medtronic_inpen"
        assert result.beacon_type == "medtronic_inpen"
        assert result.device_class == "medical"
        assert result.metadata["device_name"] == "InPen"

    def test_in_range_mirrors_app_rssi_gate(self, parser):
        assert parser.parse(make_raw(service_uuids=["bfd0"], rssi=-94)).metadata["in_range"] is True
        assert parser.parse(make_raw(service_uuids=["bfd0"], rssi=-96)).metadata["in_range"] is False


class TestIdentity:
    def test_identity_hash_uses_pen_id(self, parser):
        raw = make_raw(service_uuids=["bfd0"], service_data={"bfd0": bytes.fromhex("002c1b0a")})
        expected = hashlib.sha256(b"inpen:0a1b2c").hexdigest()[:16]
        assert parser.parse(raw).identifier_hash == expected

    def test_identity_hash_is_mac_independent(self, parser):
        a = parser.parse(make_raw(
            service_uuids=["bfd0"],
            service_data={"bfd0": bytes.fromhex("002c1b0a")},
        ))
        b = parser.parse(make_raw(
            mac_address="11:22:33:44:55:66",
            service_uuids=["bfd0"],
            service_data={"bfd0": bytes.fromhex("002c1b0a")},
        ))
        assert a.identifier_hash == b.identifier_hash

    def test_identity_falls_back_to_mac(self, parser):
        result = parser.parse(make_raw(service_uuids=["bfd0"]))
        assert result.identifier_hash == hashlib.sha256(
            b"inpen:AA:BB:CC:DD:EE:FF"
        ).hexdigest()[:16]


class TestNegatives:
    def test_returns_none_without_inpen_uuid(self, parser):
        raw = make_raw(service_uuids=["180a"], manufacturer_data=bytes.fromhex("0701" "04332211"))
        assert parser.parse(raw) is None

    def test_short_payload_is_presence_only(self, parser):
        raw = make_raw(service_uuids=["bfd0"], service_data={"bfd0": b"\x01"})
        result = parser.parse(raw)
        assert result is not None
        assert "pen_id" not in result.metadata

    def test_storage_schema_is_none(self, parser):
        assert parser.storage_schema() is None
