"""Tests for the Renogy DC Home plugin.

Ground truth: apk-ble-hunting report ``renogy-dchome_passive.md``
(``com.renogy.dchome``, Stage 4b).  Renogy broadcasts no telemetry — discovery
is by BLE local-name prefix, and the only manufacturer-data decode in the whole
app is the ``RTMShunt*`` model ID at payload bytes 4..7.
"""

import hashlib

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.renogy import (
    RenogyParser,
    RENOGY_NAME_PATTERN,
    MODEL_PREFIXES,
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


def _registry():
    reg = ParserRegistry()

    @register_parser(
        name="renogy", local_name_pattern=RENOGY_NAME_PATTERN,
        description="Renogy", version="1.0.0", core=False, registry=reg,
    )
    class _P(RenogyParser):
        pass

    return reg


class TestRenogyMatching:
    @pytest.mark.parametrize("name", [
        "RTMShunt",
        "RTMShunt1234",
        "RNGSHUNT500",
        "RNGPMS1260",
        "RNGUSBATP100",
        "RNGRBC3050",
        "RNG-CTRL-RVR40",
        "RBC2150",
        "BTRIC2112",
        "BTRIV1234",
        "BTRAC0001",
        "BTRI213AB",
        "BTRIL23XY",
        "RENOGY FrostBox",
        "Renogy FrostBox",
    ])
    def test_matches_renogy_names(self, name):
        assert len(_registry().match(_make_ad(local_name=name))) == 1

    @pytest.mark.parametrize("name", [
        "TPMS_1A2B",      # already owned by the tpms plugin
        "A1",             # 2-char prefix, far too generic to claim
        "BT",             # bare BT prefix — matches half the world
        "BT-05",
        "Bose QC35",
        "RNGB",           # no: needs the documented families
        "MyRBC21",        # prefix must anchor at the start
    ])
    def test_does_not_match_generic_names(self, name):
        assert _registry().match(_make_ad(local_name=name)) == []

    def test_no_name_no_match(self):
        assert _registry().match(_make_ad(manufacturer_data=b"\x01\x00abcdefgh")) == []


class TestRenogyParse:
    def test_presence_only_for_non_shunt(self):
        result = RenogyParser().parse(_make_ad(local_name="RNG-CTRL-RVR40"))
        assert result is not None
        assert result.parser_name == "renogy"
        assert result.beacon_type == "renogy"
        assert result.device_class == "energy"
        assert result.metadata["local_name"] == "RNG-CTRL-RVR40"
        assert result.metadata["product_family"] == "charge controller"
        assert result.metadata["telemetry"] is False
        assert "model_id" not in result.metadata

    def test_rtmshunt_model_id_from_payload_bytes_4_7(self):
        """MBlueBean.f(): payload[4..7] hex-encoded uppercase (inclusive range)."""
        payload = bytes.fromhex("00112233" "1a2b3c4d" "ffff")
        ad = _make_ad(
            local_name="RTMShunt",
            manufacturer_data=b"\x01\x00" + payload,
        )
        result = RenogyParser().parse(ad)
        assert result.metadata["model_id"] == "1A2B3C4D"
        assert result.metadata["product_family"] == "shunt"
        assert result.metadata["model"] == "Shunt300"

    def test_rtmshunt_short_payload_has_no_model_id(self):
        """The app guards on length < 8 → empty model ID."""
        ad = _make_ad(
            local_name="RTMShunt",
            manufacturer_data=b"\x01\x00" + bytes.fromhex("00112233" "1a2b"),
        )
        result = RenogyParser().parse(ad)
        assert result is not None
        assert "model_id" not in result.metadata

    def test_model_id_ignored_for_non_shunt_names(self):
        """The decode is gated on the name starting with RTMShunt."""
        ad = _make_ad(
            local_name="RNGSHUNT500",
            manufacturer_data=b"\x01\x00" + bytes.fromhex("001122331a2b3c4d"),
        )
        result = RenogyParser().parse(ad)
        assert "model_id" not in result.metadata
        assert result.metadata["model"] == "Shunt500"

    def test_company_id_is_reported_not_matched_on(self):
        """The app reads valueAt(0) blindly — the CID is informational only."""
        ad = _make_ad(
            local_name="RTMShunt",
            manufacturer_data=b"\xcb\x0e" + bytes.fromhex("001122331a2b3c4d"),
        )
        result = RenogyParser().parse(ad)
        assert result.metadata["company_id"] == 0x0ECB
        assert result.metadata["model_id"] == "1A2B3C4D"

    @pytest.mark.parametrize("name,model", [
        ("RNGUSBATP100X", "RBT12100LFP-SHBT"),
        ("RNGSHUNT500", "Shunt500"),
        ("RTMShunt77", "Shunt300"),
        ("RNGPMS1260", "RSHCB-B02P-G1"),
    ])
    def test_model_catalog(self, name, model):
        result = RenogyParser().parse(_make_ad(local_name=name))
        assert result.metadata["model"] == model

    @pytest.mark.parametrize("name,family", [
        ("RNG-CTRL-RVR40", "charge controller"),
        ("RCC30", "charge controller"),
        ("RBC2150", "dc-dc charger"),
        ("RNGRBC3050", "dc-dc charger"),
        ("BTRIC2112", "inverter"),
        ("RENOGY FrostBox", "fridge"),
        ("RNGUSBATP100", "battery"),
        ("RNGPMS1260", "gateway"),
    ])
    def test_product_family(self, name, family):
        result = RenogyParser().parse(_make_ad(local_name=name))
        assert result.metadata["product_family"] == family

    def test_name_matching_is_case_insensitive(self):
        """q4/b.java:80-90 matches the prefix case-insensitively."""
        result = RenogyParser().parse(_make_ad(local_name="rtmshunt99"))
        assert result is not None
        assert result.metadata["model"] == "Shunt300"

    def test_identity_hash_uses_mac(self):
        """No serial or per-unit ID is broadcast; BT-1/BT-2 use a static public
        address, so the MAC is the only stable anchor."""
        ad = _make_ad(local_name="RTMShunt", mac_address="11:22:33:44:55:66")
        result = RenogyParser().parse(ad)
        assert result.identifier_hash == hashlib.sha256(
            b"renogy:11:22:33:44:55:66"
        ).hexdigest()[:16]

    def test_model_id_is_not_a_serial(self):
        """Two units of the same model share the model ID — it must not be the
        identity anchor."""
        payload = b"\x01\x00" + bytes.fromhex("001122331a2b3c4d")
        a = RenogyParser().parse(
            _make_ad(local_name="RTMShunt", manufacturer_data=payload,
                     mac_address="11:22:33:44:55:66"))
        b = RenogyParser().parse(
            _make_ad(local_name="RTMShunt", manufacturer_data=payload,
                     mac_address="AA:BB:CC:00:11:22"))
        assert a.metadata["model_id"] == b.metadata["model_id"]
        assert a.identifier_hash != b.identifier_hash

    def test_unmatched_name_returns_none(self):
        assert RenogyParser().parse(_make_ad(local_name="Bose QC35")) is None

    def test_no_name_returns_none(self):
        assert RenogyParser().parse(_make_ad()) is None

    def test_raw_payload_hex_is_full_manufacturer_payload(self):
        payload = bytes.fromhex("001122331a2b3c4dffff")
        ad = _make_ad(local_name="RTMShunt", manufacturer_data=b"\x01\x00" + payload)
        assert RenogyParser().parse(ad).raw_payload_hex == payload.hex()

    def test_model_prefixes_are_longest_first(self):
        """Longer, more specific SKU prefixes must win over shorter families."""
        keys = list(MODEL_PREFIXES)
        assert keys == sorted(keys, key=len, reverse=True)
