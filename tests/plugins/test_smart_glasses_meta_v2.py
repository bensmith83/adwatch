"""Tests for Ray-Ban Meta V2 manufacturer-data decode in smart_glasses.

Source: apk-ble-hunting reports/facebook-stella_{passive,native}.md.
Offsets are post-CID (== RawAdvertisement.manufacturer_payload).
"""

import hashlib

import pytest

from adwatch.models import RawAdvertisement
from adwatch.plugins.smart_glasses import SmartGlassesParser

DEVICE_ID = bytes.fromhex("0102030405060708a9")


def _ad(payload, cid=0x01AB, mac="AA:BB:CC:DD:EE:FF"):
    return RawAdvertisement(
        timestamp="2026-10-01T00:00:00Z", mac_address=mac, address_type="random",
        manufacturer_data=cid.to_bytes(2, "little") + payload, service_data=None,
    )


def v2(flags=0x01, seed=0x00, device_id=DEVICE_ID, model=(0x01, 0x06), tail=b"\xaa\xbb\xcc"):
    return bytes([0x80, model[0], model[1], seed, flags]) + device_id + tail


@pytest.fixture
def parser():
    return SmartGlassesParser()


class TestMetaV2:
    def test_v2_decoded(self, parser):
        m = parser.parse(_ad(v2())).metadata
        assert m["meta_format"] == "v2"
        assert m["model_id"] == 0x0601
        assert m["model_name"] == "Ray-Ban Meta"
        assert m["has_owner"] is True
        assert m["pairing_seed"] == 0
        assert m["device_id"] == DEVICE_ID.hex()
        # pre-existing fields still present
        assert m["manufacturer"] == "Meta Platforms"
        assert m["company_id"] == "0x01ab"

    def test_no_owner(self, parser):
        assert parser.parse(_ad(v2(flags=0x02))).metadata["has_owner"] is False

    def test_unknown_model(self, parser):
        m = parser.parse(_ad(v2(model=(0x34, 0x12)))).metadata
        assert m["model_id"] == 0x1234
        assert m["model_name"] == "Unknown Meta device"

    def test_identity_from_device_id_not_mac(self, parser):
        r1 = parser.parse(_ad(v2(flags=1, tail=b"\x00\x00\x00"), mac="11:11:11:11:11:11"))
        r2 = parser.parse(_ad(v2(flags=0, tail=b"\xff\xff\xff"), mac="22:22:22:22:22:22"))
        expected = hashlib.sha256(f"meta_glasses:{DEVICE_ID.hex()}".encode()).hexdigest()[:16]
        assert r1.identifier_hash == expected == r2.identifier_hash

    def test_v2_min_length_14(self, parser):
        payload = v2(tail=b"")  # exactly 14 bytes
        assert len(payload) == 14
        assert parser.parse(_ad(payload)).metadata["meta_format"] == "v2"

    def test_v2_too_short_falls_back_to_generic(self, parser):
        payload = v2(tail=b"")[:13]
        r = parser.parse(_ad(payload))
        assert r is not None
        assert "meta_format" not in r.metadata
        expected = hashlib.sha256(f"AA:BB:CC:DD:EE:FF:{payload.hex()}".encode()).hexdigest()[:16]
        assert r.identifier_hash == expected

    def test_non_v2_meta_unchanged(self, parser):
        payload = bytes([0x01, 0x06, 0x01]) + bytes(14)
        r = parser.parse(_ad(payload))
        assert "meta_format" not in r.metadata
        expected = hashlib.sha256(f"AA:BB:CC:DD:EE:FF:{payload.hex()}".encode()).hexdigest()[:16]
        assert r.identifier_hash == expected

    @pytest.mark.parametrize("cid", [0x058E, 0x0D53, 0x03C2])
    def test_v2_shape_only_decoded_for_0x01ab(self, parser, cid):
        r = parser.parse(_ad(v2(), cid=cid))
        assert "meta_format" not in r.metadata
