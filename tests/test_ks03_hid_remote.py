"""Tests for KS03 generic BLE HID remote (selfie shutter / page turner)."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.ks03_hid_remote import KS03HidRemoteParser, KS03_NAME_PATTERN, KS03_PLACEHOLDER_MFG


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


def _make_registry():
    registry = ParserRegistry()

    @register_parser(
        name="ks03_hid_remote",
        local_name_pattern=KS03_NAME_PATTERN,
        description="KS03 generic BLE HID remote",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(KS03HidRemoteParser):
        pass

    return registry


class TestKS03Registry:
    def test_matches_local_name_pattern(self):
        registry = _make_registry()
        ad = _make_ad(local_name="KS03~2520e0")
        assert len(registry.match(ad)) >= 1

    def test_matches_uppercase_hex(self):
        registry = _make_registry()
        ad = _make_ad(local_name="KS03~ABCDEF")
        assert len(registry.match(ad)) >= 1

    def test_no_match_unrelated_name(self):
        registry = _make_registry()
        ad = _make_ad(local_name="Something")
        assert len(registry.match(ad)) == 0

    def test_no_match_short_suffix(self):
        registry = _make_registry()
        # Pattern expects a 6-char hex suffix; reject anything shorter
        ad = _make_ad(local_name="KS03~abc")
        assert len(registry.match(ad)) == 0


class TestKS03Parser:
    def test_parses_canonical_name(self):
        parser = KS03HidRemoteParser()
        ad = _make_ad(local_name="KS03~2520e0")
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "ks03_hid_remote"
        assert result.beacon_type == "ks03_hid_remote"
        assert result.device_class == "remote"

    def test_mac_suffix_extracted(self):
        parser = KS03HidRemoteParser()
        ad = _make_ad(local_name="KS03~98dad0")
        result = parser.parse(ad)
        assert result.metadata["mac_suffix"] == "98dad0"

    def test_device_name_preserved(self):
        parser = KS03HidRemoteParser()
        ad = _make_ad(local_name="KS03~2520e0")
        result = parser.parse(ad)
        assert result.metadata["device_name"] == "KS03~2520e0"

    def test_flags_placeholder_mfg_data(self):
        """Mfg data f001020304050600 is a Telink SDK uninitialized template."""
        parser = KS03HidRemoteParser()
        ad = _make_ad(
            local_name="KS03~2520e0",
            manufacturer_data=KS03_PLACEHOLDER_MFG,
        )
        result = parser.parse(ad)
        assert result.metadata["mfg_placeholder"] is True
        assert result.metadata["claimed_company_id"] == "0x01F0"

    def test_does_not_flag_real_mfg_data(self):
        parser = KS03HidRemoteParser()
        ad = _make_ad(
            local_name="KS03~2520e0",
            manufacturer_data=b"\xf0\x01\xde\xad\xbe\xef",
        )
        result = parser.parse(ad)
        assert result.metadata.get("mfg_placeholder") is False

    def test_identity_hash_stable(self):
        parser = KS03HidRemoteParser()
        mac = "11:22:33:44:55:66"
        ad = _make_ad(mac_address=mac, local_name="KS03~2520e0")
        result = parser.parse(ad)
        expected = hashlib.sha256(f"{mac}:ks03_hid_remote".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_returns_none_without_name(self):
        parser = KS03HidRemoteParser()
        ad = _make_ad()
        assert parser.parse(ad) is None

    def test_returns_none_for_wrong_name(self):
        parser = KS03HidRemoteParser()
        ad = _make_ad(local_name="KS04~123456")
        assert parser.parse(ad) is None

    def test_hid_service_flagged(self):
        parser = KS03HidRemoteParser()
        ad = _make_ad(
            local_name="KS03~2520e0",
            service_uuids=["1812", "180F"],
        )
        result = parser.parse(ad)
        assert result.metadata["advertises_hid"] is True
