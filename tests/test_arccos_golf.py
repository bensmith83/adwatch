"""Tests for Arccos Golf grip sensor / Link hub plugin.

Byte layout per apk-ble-hunting/reports/arccosgolf-androidflagship_passive.md.
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.arccos_golf import (
    ArccosGolfParser,
    ARCCOS_SERVICE_UUID,
    ARCCOS_NAME_PATTERN,
    SHOT_TYPES,
    REJECTED_NAME,
)


def _make_ad(**kwargs):
    defaults = {
        "timestamp": "2026-08-16T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "public",
        "manufacturer_data": None,
        "service_data": None,
        "service_uuids": [ARCCOS_SERVICE_UUID],
    }
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _sensor_frame(sensor_id=b"\x11\x22\x33\x44\x55\x66", battery=84, movement=1,
                  shot_type=2, seconds=7, hitcount=5, xyz=1, reset=0, reason=0,
                  x=10, y=-3, z=120) -> bytes:
    """Build a grip-sensor advert as adwatch sees it.

    The whole manufacturer-specific AD payload is scan-record bytes [5..],
    so manufacturer_data[i] == scan_record[5 + i].
    """
    b11 = ((battery & 0x7F) << 1) | (movement & 1)
    b14 = ((hitcount & 0xF) << 4) | ((xyz & 1) << 3) | ((reset & 1) << 2) | (reason & 3)
    return (
        sensor_id
        + bytes([b11, shot_type, seconds, b14])
        + bytes([x & 0xFF, y & 0xFF, z & 0xFF])
    )


def _register(registry):
    @register_parser(
        name="arccos_golf",
        service_uuid=ARCCOS_SERVICE_UUID,
        local_name_pattern=ARCCOS_NAME_PATTERN,
        description="Arccos Golf",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(ArccosGolfParser):
        pass

    return registry


class TestMatching:
    def test_matches_service_uuid(self):
        reg = _register(ParserRegistry())
        assert len(reg.match(_make_ad(manufacturer_data=_sensor_frame()))) == 1

    def test_matches_link_hub_name(self):
        reg = _register(ParserRegistry())
        for name in ("Arccos Link", "link1a2b", "LNK3FF01", "rf00c3"):
            ad = _make_ad(service_uuids=[], local_name=name)
            assert len(reg.match(ad)) == 1, name

    def test_ignores_unrelated_name(self):
        reg = _register(ParserRegistry())
        assert reg.match(_make_ad(service_uuids=[], local_name="linkedin")) == []


class TestGripSensorDecode:
    def test_full_frame_decode(self):
        r = ArccosGolfParser().parse(_make_ad(manufacturer_data=_sensor_frame()))
        assert r is not None
        assert r.parser_name == "arccos_golf"
        assert r.metadata["device_role"] == "grip_sensor"
        assert r.metadata["sensor_id"] == "112233445566"
        assert r.metadata["sensor_mac_style"] == "11:22:33:44:55:66"
        assert r.metadata["battery_level"] == 84
        assert r.metadata["movement"] is True
        assert r.metadata["shot_type"] == SHOT_TYPES[2]
        assert r.metadata["shot_type_value"] == 2
        assert r.metadata["seconds_since_shot"] == 7
        assert r.metadata["hitcount"] == 5
        assert r.metadata["xyz_valid"] is True
        assert r.metadata["reset_flag"] is False
        assert r.metadata["reset_reason"] == 0

    def test_accelerometer_is_signed(self):
        r = ArccosGolfParser().parse(
            _make_ad(manufacturer_data=_sensor_frame(x=10, y=-3, z=120)))
        assert r.metadata["accel_x"] == 10
        assert r.metadata["accel_y"] == -3
        assert r.metadata["accel_z"] == 120

    def test_shot_type_names(self):
        p = ArccosGolfParser()
        for value, label in SHOT_TYPES.items():
            r = p.parse(_make_ad(manufacturer_data=_sensor_frame(shot_type=value)))
            assert r.metadata["shot_type"] == label

    def test_hit_event_flag(self):
        p = ArccosGolfParser()
        assert p.parse(_make_ad(
            manufacturer_data=_sensor_frame(shot_type=2))).metadata["is_shot"] is True
        assert p.parse(_make_ad(
            manufacturer_data=_sensor_frame(shot_type=1))).metadata["is_shot"] is False

    def test_movement_and_reset_bits(self):
        r = ArccosGolfParser().parse(_make_ad(
            manufacturer_data=_sensor_frame(movement=0, reset=1, reason=3, xyz=0)))
        assert r.metadata["movement"] is False
        assert r.metadata["reset_flag"] is True
        assert r.metadata["reset_reason"] == 3
        assert r.metadata["xyz_valid"] is False

    def test_identity_from_sensor_id_not_mac(self):
        p = ArccosGolfParser()
        a = _make_ad(mac_address="11:22:33:44:55:66",
                     manufacturer_data=_sensor_frame(hitcount=1))
        b = _make_ad(mac_address="99:88:77:66:55:44",
                     manufacturer_data=_sensor_frame(hitcount=9))
        assert p.parse(a).identifier_hash == p.parse(b).identifier_hash
        assert p.parse(a).identifier_hash == hashlib.sha256(
            b"arccos:112233445566").hexdigest()[:16]

    def test_stable_key_ignores_volatile_telemetry(self):
        r = ArccosGolfParser().parse(_make_ad(manufacturer_data=_sensor_frame()))
        assert r.stable_key == "arccos:112233445566"


class TestGripSensorGating:
    def test_rejects_short_payload(self):
        ad = _make_ad(manufacturer_data=_sensor_frame()[:12])
        assert ArccosGolfParser().parse(ad) is None

    def test_rejects_out_of_range_shot_type(self):
        ad = _make_ad(manufacturer_data=_sensor_frame(shot_type=9))
        assert ArccosGolfParser().parse(ad) is None

    def test_rejects_impossible_battery(self):
        ad = _make_ad(manufacturer_data=_sensor_frame(battery=120))
        assert ArccosGolfParser().parse(ad) is None

    def test_rejects_unprovisioned_ti_keyfob(self):
        ad = _make_ad(manufacturer_data=_sensor_frame(), local_name=REJECTED_NAME)
        assert ArccosGolfParser().parse(ad) is None

    def test_rejects_bare_fff0_device(self):
        # 0xFFF0 is a generic squatted UUID — no Arccos-shaped payload, no match.
        ad = _make_ad(manufacturer_data=bytes.fromhex("0102"), local_name="BM2")
        assert ArccosGolfParser().parse(ad) is None


class TestLinkAndRangefinder:
    def test_link_hub_name_id(self):
        r = ArccosGolfParser().parse(_make_ad(service_uuids=[], local_name="link1a2b"))
        assert r is not None
        assert r.metadata["device_role"] == "link_hub"
        assert r.metadata["unit_id"] == "1a2b"

    def test_lnk3_variant(self):
        r = ArccosGolfParser().parse(_make_ad(service_uuids=[], local_name="LNK3FF01"))
        assert r.metadata["device_role"] == "link_hub"
        assert r.metadata["unit_id"] == "FF01"

    def test_rangefinder(self):
        r = ArccosGolfParser().parse(_make_ad(service_uuids=[], local_name="rf00c3"))
        assert r.metadata["device_role"] == "rangefinder"
        assert r.metadata["unit_id"] == "00c3"

    def test_generic_arccos_link_name(self):
        r = ArccosGolfParser().parse(_make_ad(service_uuids=[], local_name="Arccos Link"))
        assert r.metadata["device_role"] == "link_hub"
        assert "unit_id" not in r.metadata

    def test_identity_from_name_id(self):
        r = ArccosGolfParser().parse(_make_ad(service_uuids=[], local_name="link1a2b"))
        assert r.identifier_hash == hashlib.sha256(
            b"arccos:link:1a2b").hexdigest()[:16]

    def test_unrelated_name_returns_none(self):
        assert ArccosGolfParser().parse(
            _make_ad(service_uuids=[], local_name="linkedin")) is None
