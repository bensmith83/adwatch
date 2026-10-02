"""Tests for Even Realities G1 detection in smart_glasses.

Source: apk-ble-hunting reports/even-g1_{passive,native}.md. The G1 exposes
two peripherals per pair (left/right temple), discovered by local name only
(`Even G1_<id>_L` / `_R`); no manufacturer/service-data telemetry. NUS
6e400001-... is generic Nordic and must not be claimed on its own.
"""

import hashlib

import pytest

from adwatch.models import RawAdvertisement
from adwatch.plugins.smart_glasses import SmartGlassesParser

NUS = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"


def _ad(name=None, mfr=None, uuids=None, mac="AA:BB:CC:DD:EE:FF"):
    return RawAdvertisement(
        timestamp="2026-10-01T00:00:00Z", mac_address=mac, address_type="random",
        manufacturer_data=mfr, service_data=None, service_uuids=uuids or [],
        local_name=name,
    )


@pytest.fixture
def parser():
    return SmartGlassesParser()


def _entry_matches(ad):
    import adwatch.plugins.smart_glasses  # noqa: F401
    from adwatch.registry import _default_registry
    entry = next(e for e in _default_registry._parsers if e["name"] == "smart_glasses")
    return _default_registry._entry_matches(entry, ad)


class TestEvenG1:
    def test_left_temple(self, parser):
        r = parser.parse(_ad("Even G1_74_L"))
        assert r is not None
        m = r.metadata
        assert m["manufacturer"] == "Even Realities"
        assert m["model_name"] == "Even G1"
        assert m["pair_id"] == "74"
        assert m["side"] == "left"
        assert r.device_class == "wearable"

    def test_right_temple(self, parser):
        m = parser.parse(_ad("Even G1_74_R")).metadata
        assert m["side"] == "right"
        assert m["pair_id"] == "74"

    def test_trailing_token_variant(self, parser):
        """Field names seen as `Even G1_<id>_L_<suffix>` are also accepted."""
        m = parser.parse(_ad("Even G1_87_L_39E92")).metadata
        assert m["pair_id"] == "87"
        assert m["side"] == "left"
        assert m["name_suffix"] == "39E92"

    def test_prefix_only_name(self, parser):
        m = parser.parse(_ad("Even G1")).metadata
        assert m["model_name"] == "Even G1"
        assert "side" not in m

    def test_identity_per_temple_from_name(self, parser):
        a = parser.parse(_ad("Even G1_74_L", mac="11:11:11:11:11:11"))
        b = parser.parse(_ad("Even G1_74_L", mac="22:22:22:22:22:22"))
        c = parser.parse(_ad("Even G1_74_R"))
        assert a.identifier_hash == b.identifier_hash
        assert a.identifier_hash != c.identifier_hash
        assert a.identifier_hash == hashlib.sha256(b"even_g1:Even G1_74_L").hexdigest()[:16]

    def test_nus_corroboration_flag(self, parser):
        assert parser.parse(_ad("Even G1_74_L", uuids=[NUS])).metadata["nus_service"] is True

    def test_name_with_unrelated_mfr_data(self, parser):
        r = parser.parse(_ad("Even G1_74_L", mfr=b"\x59\x00\x01\x02"))
        assert r.metadata["model_name"] == "Even G1"

    def test_registry_matches_name(self):
        assert _entry_matches(_ad("Even G1_74_R"))

    def test_registry_does_not_claim_nus_alone(self):
        assert not _entry_matches(_ad("Nordic_UART", uuids=[NUS]))

    def test_non_even_name_rejected(self, parser):
        assert parser.parse(_ad("Evening G1")) is None
        assert parser.parse(_ad("Even G2_1_L")) is None

    def test_meta_path_unaffected_by_name(self, parser):
        payload = bytes([0x80, 0x01, 0x06, 0x00, 0x01]) + bytes(9)
        r = parser.parse(_ad("Ray-Ban Meta", mfr=b"\xab\x01" + payload))
        assert r.metadata["meta_format"] == "v2"
