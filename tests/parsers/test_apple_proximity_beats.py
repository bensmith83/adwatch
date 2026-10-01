"""Tests for Beats (apple-bnd) enrichment of the Apple Proximity Pairing parser.

Source: apk-ble-hunting reports/apple-bnd_passive.md (Beats app p1/e.java +
p1/f.java). Offsets below are into the manufacturer payload (after the 2-byte
Apple CID 0x004C), i.e. ``msd`` == RawAdvertisement.manufacturer_payload.
"""

import hashlib

import pytest

from adwatch.models import RawAdvertisement
from adwatch.parsers.apple_proximity import AppleProximityParser


@pytest.fixture
def parser():
    return AppleProximityParser()


def make_raw(msd, mac="AA:BB:CC:DD:EE:FF"):
    return RawAdvertisement(
        timestamp="2026-10-01T00:00:00+00:00",
        mac_address=mac,
        address_type="random",
        manufacturer_data=b"\x4c\x00" + bytes(msd),
        service_data=None,
    )


ADDR = bytes([0x11, 0x22, 0x33, 0x44, 0x55, 0x66])


def b2p_msd(addr=ADDR, right=0x80 | 85, left=90, case=0x80 | 50, color=0x03,
            flags=0x00, lid=0x00, pid=(0x16, 0x20)):
    """B2P extended layout: 07 <len> 00 <pid_lo> <pid_hi> <addr x6> ..."""
    msd = bytearray([0x07, 0x19, 0x00, pid[0], pid[1]])
    msd += addr                       # 5-10
    msd += bytes([flags])             # 11
    msd += bytes([right, left, case])  # 12-14
    msd += bytes([color])             # 15
    msd += bytes([lid])               # 16
    msd += bytes(10)                  # trailing (encrypted/other) bytes
    return bytes(msd)


class TestProductIdLE:
    def test_compact_layout_exposes_product_id_le(self, parser):
        # Standard AirPods-style compact ad (msd[2] != 0)
        msd = bytes([0x07, 0x19, 0x01, 0x14, 0x20, 0x24, 0x89, 0x60, 0x02]) + bytes(18)
        r = parser.parse(make_raw(msd))
        assert r.metadata["product_id"] == 0x2014
        assert r.metadata["layout"] == "compact"
        # legacy big-endian form is preserved
        assert r.metadata["device_model"] == 0x1420


class TestBeatsB2PExtended:
    def test_family_and_layout(self, parser):
        r = parser.parse(make_raw(b2p_msd()))
        assert r is not None
        assert r.metadata["layout"] == "extended"
        assert r.metadata["beats_family"] == "B2P"
        assert r.metadata["product_id"] == 0x2016

    def test_batteries_and_charging(self, parser):
        r = parser.parse(make_raw(b2p_msd()))
        m = r.metadata
        assert m["battery_right"] == 85
        assert m["battery_left"] == 90
        assert m["battery_case"] == 50
        assert m["charging_right"] is True
        assert m["charging_left"] is False
        assert m["charging_case"] is True

    def test_device_address(self, parser):
        r = parser.parse(make_raw(b2p_msd()))
        assert r.metadata["device_address"] == "11:22:33:44:55:66"

    def test_color(self, parser):
        r = parser.parse(make_raw(b2p_msd(color=0x8D)))
        assert r.metadata["color_id"] == 0x8D & 0x07

    def test_extended_layout_drops_compact_only_fields(self, parser):
        r = parser.parse(make_raw(b2p_msd()))
        # utp / in-ear nibbles are address bytes in this layout
        assert "utp" not in r.metadata
        assert "in_ear_left" not in r.metadata

    def test_identity_uses_persistent_address(self, parser):
        r1 = parser.parse(make_raw(b2p_msd(), mac="AA:AA:AA:AA:AA:01"))
        r2 = parser.parse(make_raw(b2p_msd(right=40, left=40), mac="BB:BB:BB:BB:BB:02"))
        expected = hashlib.sha256(b"beats:11:22:33:44:55:66").hexdigest()[:16]
        assert r1.identifier_hash == expected
        assert r2.identifier_hash == expected

    def test_bcd_family_no_address(self, parser):
        msd = bytearray(b2p_msd())
        msd[1] = 0x0F  # BCD prefix 07 0F 00
        r = parser.parse(make_raw(bytes(msd)))
        assert r.metadata["beats_family"] == "BCD"
        assert "device_address" not in r.metadata
        assert r.metadata["battery_left"] == 90

    def test_short_extended_falls_back_to_compact(self, parser):
        # msd[2]==0 but < 17 bytes -> not decodable as extended; old compact path
        msd = bytes([0x07, 0x19, 0x00, 0x16, 0x20, 0x24, 0x89, 0x60, 0x02])
        r = parser.parse(make_raw(msd))
        assert r is not None
        assert r.metadata["layout"] == "compact"
        assert "beats_family" not in r.metadata


class TestBeatsBTP:
    def btp_msd(self, first=0x00):
        # <any> 90 <pid_lo> <pid_hi> ... compact nibbles at msd[6]/msd[7]
        return bytes([first, 0x90, 0x26, 0x20, 0x00, 0x00, 0x7A, 0x05]) + bytes(9)

    def test_btp_detected(self, parser):
        r = parser.parse(make_raw(self.btp_msd()))
        assert r is not None
        assert r.metadata["beats_family"] == "BTP"
        assert r.metadata["product_id"] == 0x2026

    def test_btp_batteries(self, parser):
        r = parser.parse(make_raw(self.btp_msd()))
        assert r.metadata["battery_right"] == 100
        assert r.metadata["battery_left"] == 70
        assert r.metadata["battery_case"] == 50

    def test_btp_with_proximity_type_byte(self, parser):
        r = parser.parse(make_raw(self.btp_msd(first=0x07)))
        assert r.metadata["beats_family"] == "BTP"

    def test_btp_not_claimed_when_type_owned_by_other_apple_parser(self, parser):
        # 0x10 = Nearby Info (apple_continuity) -- don't double-claim
        assert parser.parse(make_raw(self.btp_msd(first=0x10))) is None

    def test_btp_too_short(self, parser):
        assert parser.parse(make_raw(bytes([0x00, 0x90, 0x26]))) is None
