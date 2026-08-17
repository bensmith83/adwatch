"""Tests for the Mobvoi TicWatch plugin.

Per apk-ble-hunting/reports/mobvoi-ticwatch_passive.md.
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.mobvoi_ticwatch import (
    MobvoiTicwatchParser,
    TICWATCH_NAME_PATTERN,
    MOBVOI_COMPANION_COMPANY_ID,
)


def _make_ad(**kw):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "F0:0D:11:22:33:44",
        "address_type": "random",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(
        name="mobvoi_ticwatch",
        local_name_pattern=TICWATCH_NAME_PATTERN,
        description="TicWatch",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(MobvoiTicwatchParser):
        pass

    return _P


class TestTicwatchMatching:
    def test_matches_ticwatch_pro(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(local_name="TicWatch Pro"))) == 1

    def test_matches_bare_ticwatch(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(local_name="TicWatch"))) == 1

    def test_glued_suffix_does_not_match(self):
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(_make_ad(local_name="TicWatchery")) == []

    def test_mid_name_does_not_match(self):
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(_make_ad(local_name="My TicWatch Pro")) == []

    def test_mediatek_company_id_not_registered(self):
        """0x0046 is MediaTek's SIG CID, not Mobvoi's — never a match basis."""
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=bytes([0x46, 0x00, 0x7B, 0x1C, 0xE4]))
        assert registry.match(ad) == []


class TestTicwatchDecode:
    def test_model_hint_pro(self):
        result = MobvoiTicwatchParser().parse(_make_ad(local_name="TicWatch Pro"))
        assert result is not None
        assert result.metadata["model_hint"] == "Pro"
        assert result.metadata["device_name"] == "TicWatch Pro"

    def test_model_hint_pro_3(self):
        result = MobvoiTicwatchParser().parse(_make_ad(local_name="TicWatch Pro 3"))
        assert result.metadata["model_hint"] == "Pro 3"

    def test_model_hint_e(self):
        result = MobvoiTicwatchParser().parse(_make_ad(local_name="TicWatch E"))
        assert result.metadata["model_hint"] == "E"

    def test_bracketed_suffix_split_out(self):
        result = MobvoiTicwatchParser().parse(
            _make_ad(local_name="TicWatch Pro [A1B2C3]")
        )
        assert result.metadata["model_hint"] == "Pro"
        assert result.metadata["name_suffix"] == "A1B2C3"

    def test_bare_name_has_no_model_hint(self):
        result = MobvoiTicwatchParser().parse(_make_ad(local_name="TicWatch"))
        assert result is not None
        assert "model_hint" not in result.metadata

    def test_rejects_glued_suffix(self):
        assert MobvoiTicwatchParser().parse(_make_ad(local_name="TicWatchery")) is None

    def test_rejects_missing_name(self):
        assert MobvoiTicwatchParser().parse(_make_ad()) is None

    def test_rejects_unrelated_name(self):
        assert MobvoiTicwatchParser().parse(_make_ad(local_name="Galaxy Watch")) is None


class TestTicwatchIdentityAndBasics:
    def test_identity_from_mac(self):
        ad = _make_ad(local_name="TicWatch Pro")
        result = MobvoiTicwatchParser().parse(ad)
        expected = hashlib.sha256(
            f"mobvoi_ticwatch:{ad.mac_address}".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_basics(self):
        result = MobvoiTicwatchParser().parse(_make_ad(local_name="TicWatch Pro"))
        assert result.parser_name == "mobvoi_ticwatch"
        assert result.beacon_type == "mobvoi_ticwatch"
        assert result.device_class == "wearable"
        assert result.metadata["vendor"] == "Mobvoi"
        assert result.metadata["platform"] == "Wear OS"

    def test_companion_company_id_constant_documented(self):
        """Kept as documentation of the phone-side advert, deliberately unused."""
        assert MOBVOI_COMPANION_COMPANY_ID == 0x0046
