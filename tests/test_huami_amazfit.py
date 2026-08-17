"""Tests for Huami Mi Band / Amazfit plugin."""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.huami_amazfit import (
    HuamiAmazfitParser,
    MIBAND_LEGACY_UUID,
    HUAMI_NEW_UUID,
)


def _make_ad(**kw):
    defaults = {"timestamp": "2025-01-01T00:00:00Z", "mac_address": "AA:BB:CC:DD:EE:FF",
                "address_type": "random", "manufacturer_data": None, "service_data": None}
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(name="huami_amazfit",
                     service_uuid=[MIBAND_LEGACY_UUID, HUAMI_NEW_UUID],
                     local_name_pattern=r"^(MI Band|Mi Smart Band|Amazfit|Zepp)",
                     description="Huami", version="1.0.0", core=False,
                     registry=registry)
    class _P(HuamiAmazfitParser):
        pass
    return _P


class TestHuamiMatching:
    def test_match_legacy_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[MIBAND_LEGACY_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_new_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[HUAMI_NEW_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_amazfit_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="Amazfit Bip")
        assert len(registry.match(ad)) == 1

    def test_match_mi_smart_band(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="Mi Smart Band 6")
        assert len(registry.match(ad)) == 1


class TestHuamiParsing:
    def test_legacy_uuid_classified_as_miband_legacy(self):
        ad = _make_ad(service_uuids=[MIBAND_LEGACY_UUID])
        result = HuamiAmazfitParser().parse(ad)
        assert result is not None
        assert result.metadata["product_family"] == "mi_band_legacy"

    def test_new_uuid_classified_as_huami_new(self):
        ad = _make_ad(service_uuids=[HUAMI_NEW_UUID])
        result = HuamiAmazfitParser().parse(ad)
        assert result.metadata["product_family"] == "huami_new"

    def test_amazfit_name_extracted(self):
        ad = _make_ad(local_name="Amazfit Bip")
        result = HuamiAmazfitParser().parse(ad)
        assert result.metadata["device_name"] == "Amazfit Bip"
        assert result.metadata["model_hint"] == "Bip"

    def test_amazfit_gtr_42mm(self):
        ad = _make_ad(local_name="Amazfit GTR 42mm")
        result = HuamiAmazfitParser().parse(ad)
        assert result.metadata["model_hint"] == "GTR 42mm"

    def test_mi_band_4(self):
        ad = _make_ad(local_name="Mi Smart Band 4")
        result = HuamiAmazfitParser().parse(ad)
        assert result.metadata["model_hint"] == "Smart Band 4"

    def test_basics(self):
        ad = _make_ad(service_uuids=[HUAMI_NEW_UUID])
        result = HuamiAmazfitParser().parse(ad)
        assert result.parser_name == "huami_amazfit"
        assert result.beacon_type == "huami_amazfit"
        assert result.device_class == "wearable"

    def test_returns_none_unrelated(self):
        assert HuamiAmazfitParser().parse(_make_ad(local_name="Other")) is None


# --- Extended-advertisement telemetry (huami-watch-hmwatchmanager_passive.md) ---

from adwatch.plugins.huami_amazfit import HUAMI_COMPANY_ID  # noqa: E402


def _ext_adv(tlvs=(bytes([0x02, 0x01, 0x48]),), filler=0x00,
             hw=bytes([0xC8, 0x47, 0x8C, 0x11, 0x22, 0x33]), prefix=0x02):
    body = b"".join(tlvs)
    tail = bytes([filler]) + hw if hw is not None else b""
    return bytes([0x57, 0x01, prefix]) + body + tail


class TestHuamiExtendedAdvMatching:
    def test_matches_huami_company_id(self):
        registry = ParserRegistry()

        @register_parser(name="huami_amazfit", company_id=HUAMI_COMPANY_ID,
                         service_uuid=[MIBAND_LEGACY_UUID, HUAMI_NEW_UUID],
                         local_name_pattern=r"^(MI Band|Mi Smart Band|Amazfit|Zepp)",
                         description="Huami", version="1.0.0", core=False,
                         registry=registry)
        class _P(HuamiAmazfitParser):
            pass

        assert len(registry.match(_make_ad(manufacturer_data=_ext_adv()))) == 1

    def test_company_id_constant(self):
        assert HUAMI_COMPANY_ID == 0x0157


class TestHuamiExtendedAdvDecode:
    def test_decodes_heart_rate(self):
        result = HuamiAmazfitParser().parse(_make_ad(manufacturer_data=_ext_adv()))
        assert result is not None
        assert result.metadata["heart_rate"] == 72
        assert result.metadata["adv_format"] == "extended"

    def test_decodes_all_three_tlvs(self):
        ad = _make_ad(manufacturer_data=_ext_adv(tlvs=(
            bytes([0x02, 0x01, 0x50]),
            bytes([0x02, 0x02, 0x01]),
            bytes([0x02, 0x03, 0x00]),
        )))
        result = HuamiAmazfitParser().parse(ad)
        assert result.metadata["heart_rate"] == 80
        assert result.metadata["charging"] is True
        assert result.metadata["account_bound"] is False

    def test_bound_true_charging_false(self):
        ad = _make_ad(manufacturer_data=_ext_adv(tlvs=(
            bytes([0x02, 0x02, 0x00]),
            bytes([0x02, 0x03, 0x01]),
        )))
        result = HuamiAmazfitParser().parse(ad)
        assert result.metadata["charging"] is False
        assert result.metadata["account_bound"] is True
        assert "heart_rate" not in result.metadata

    def test_decodes_hardware_address(self):
        result = HuamiAmazfitParser().parse(_make_ad(manufacturer_data=_ext_adv()))
        assert result.metadata["hardware_address"] == "C8:47:8C:11:22:33"

    def test_unknown_tlv_types_skipped(self):
        ad = _make_ad(manufacturer_data=_ext_adv(tlvs=(
            bytes([0x03, 0x07, 0xAA, 0xBB]),
            bytes([0x02, 0x01, 0x3C]),
        )))
        result = HuamiAmazfitParser().parse(ad)
        assert result.metadata["heart_rate"] == 60

    def test_zero_length_terminates_tlv_scan(self):
        ad = _make_ad(manufacturer_data=_ext_adv(tlvs=(
            bytes([0x02, 0x01, 0x41]), bytes([0x00, 0x02, 0x01]),
        )))
        result = HuamiAmazfitParser().parse(ad)
        assert result.metadata["heart_rate"] == 65
        assert "charging" not in result.metadata

    def test_no_trailer_still_decodes_tlvs(self):
        ad = _make_ad(manufacturer_data=_ext_adv(hw=None))
        result = HuamiAmazfitParser().parse(ad)
        assert result.metadata["heart_rate"] == 72
        assert "hardware_address" not in result.metadata

    def test_wrong_prefix_byte_not_decoded(self):
        ad = _make_ad(manufacturer_data=_ext_adv(prefix=0x01))
        result = HuamiAmazfitParser().parse(ad)
        assert result is not None
        assert "heart_rate" not in result.metadata
        assert "adv_format" not in result.metadata

    def test_truncated_tlv_ignored(self):
        # declares a 4-byte TLV body but only 1 value byte is present
        ad = _make_ad(manufacturer_data=bytes([0x57, 0x01, 0x02, 0x05, 0x01, 0x48]))
        result = HuamiAmazfitParser().parse(ad)
        assert "heart_rate" not in result.metadata

    def test_wrong_company_id_not_decoded(self):
        ad = _make_ad(
            service_uuids=[HUAMI_NEW_UUID],
            manufacturer_data=bytes([0x4C, 0x00, 0x02, 0x02, 0x01, 0x48]),
        )
        result = HuamiAmazfitParser().parse(ad)
        assert "heart_rate" not in result.metadata

    def test_company_id_only_gives_product_family(self):
        result = HuamiAmazfitParser().parse(_make_ad(manufacturer_data=_ext_adv()))
        assert result.metadata["product_family"] == "huami_watch"

    def test_uuid_family_wins_over_cid(self):
        ad = _make_ad(service_uuids=[MIBAND_LEGACY_UUID], manufacturer_data=_ext_adv())
        result = HuamiAmazfitParser().parse(ad)
        assert result.metadata["product_family"] == "mi_band_legacy"
        assert result.metadata["heart_rate"] == 72

    def test_name_family_preserved_with_extended_adv(self):
        ad = _make_ad(local_name="Amazfit GTR 4", manufacturer_data=_ext_adv())
        result = HuamiAmazfitParser().parse(ad)
        assert result.metadata["model_hint"] == "GTR 4"
        assert result.metadata["heart_rate"] == 72


class TestHuamiExtendedAdvIdentity:
    def test_identity_prefers_hardware_address(self):
        ad = _make_ad(manufacturer_data=_ext_adv())
        result = HuamiAmazfitParser().parse(ad)
        expected = hashlib.sha256(
            b"huami_amazfit:C8:47:8C:11:22:33"
        ).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_survives_mac_rotation(self):
        a = _make_ad(manufacturer_data=_ext_adv(), mac_address="D0:11:22:33:44:55")
        b = _make_ad(manufacturer_data=_ext_adv(tlvs=(bytes([0x02, 0x01, 0x5A]),)),
                     mac_address="E1:66:77:88:99:AA")
        assert HuamiAmazfitParser().parse(a).identifier_hash == \
            HuamiAmazfitParser().parse(b).identifier_hash

    def test_identity_falls_back_to_mac(self):
        ad = _make_ad(service_uuids=[HUAMI_NEW_UUID])
        result = HuamiAmazfitParser().parse(ad)
        expected = hashlib.sha256(
            f"huami_amazfit:{ad.mac_address}".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected
