"""Tests for Renpho/Etekcity smart scale plugin (detection only)."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

# RED phase — this import will fail until the plugin exists
from adwatch.plugins.renpho import RenphoParser


def _make_ad(**kwargs):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "random",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


class TestRenphoParser:
    def test_match_by_company_id(self):
        """Should match by company_id 0x06D0."""
        registry = ParserRegistry()

        @register_parser(
            name="renpho", company_id=0x06D0, local_name_pattern=r"^QN-Scale$",
            description="Renpho", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(RenphoParser):
            pass

        mfr_data = struct.pack("<H", 0x06D0) + b"\x01\x02"
        ad = _make_ad(manufacturer_data=mfr_data)
        assert len(registry.match(ad)) == 1

    def test_match_by_local_name(self):
        """Should match by local_name 'QN-Scale'."""
        registry = ParserRegistry()

        @register_parser(
            name="renpho", company_id=0x06D0, local_name_pattern=r"^QN-Scale$",
            description="Renpho", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(RenphoParser):
            pass

        ad = _make_ad(local_name="QN-Scale")
        assert len(registry.match(ad)) == 1

    def test_parse_result_device_class(self):
        """Should return ParseResult with device_class='scale'."""
        registry = ParserRegistry()

        @register_parser(
            name="renpho", company_id=0x06D0, local_name_pattern=r"^QN-Scale$",
            description="Renpho", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(RenphoParser):
            pass

        mfr_data = struct.pack("<H", 0x06D0) + b"\x01\x02"
        ad = _make_ad(manufacturer_data=mfr_data, local_name="QN-Scale")
        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.device_class == "scale"

    def test_parse_result_fields(self):
        """Should return correct parser_name and beacon_type."""
        registry = ParserRegistry()

        @register_parser(
            name="renpho", company_id=0x06D0, local_name_pattern=r"^QN-Scale$",
            description="Renpho", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(RenphoParser):
            pass

        mfr_data = struct.pack("<H", 0x06D0) + b"\x01\x02"
        ad = _make_ad(manufacturer_data=mfr_data, local_name="QN-Scale")
        result = registry.match(ad)[0].parse(ad)
        assert result.parser_name == "renpho"
        assert result.beacon_type == "renpho"

    def test_identity_hash(self):
        """Identity hash: SHA256('{mac}:QN-Scale')[:16]."""
        registry = ParserRegistry()

        @register_parser(
            name="renpho", company_id=0x06D0, local_name_pattern=r"^QN-Scale$",
            description="Renpho", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(RenphoParser):
            pass

        mfr_data = struct.pack("<H", 0x06D0) + b"\x01\x02"
        ad = _make_ad(
            manufacturer_data=mfr_data,
            mac_address="11:22:33:44:55:66",
            local_name="QN-Scale",
        )
        result = registry.match(ad)[0].parse(ad)
        expected = hashlib.sha256("11:22:33:44:55:66:QN-Scale".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_no_match_wrong_company_id(self):
        """Should not match with wrong company_id and no matching name."""
        registry = ParserRegistry()

        @register_parser(
            name="renpho", company_id=0x06D0, local_name_pattern=r"^QN-Scale$",
            description="Renpho", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(RenphoParser):
            pass

        mfr_data = struct.pack("<H", 0x9999) + b"\x01\x02"
        ad = _make_ad(manufacturer_data=mfr_data, local_name="OtherDevice")
        assert len(registry.match(ad)) == 0


class TestRenphoEnrichedCatalog:
    """v2.0.0: full Qingniu OEM brand catalog."""

    def test_yolanda_brand_recognized(self):
        parser = RenphoParser()
        ad = _make_ad(local_name="Yolanda-CS20E1")
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["brand"] == "Yolanda"
        assert result.metadata["model_code"] == "CS20E1"

    def test_dretec_brand(self):
        parser = RenphoParser()
        ad = _make_ad(local_name="Dretec-CS50A")
        result = parser.parse(ad)
        assert result.metadata["brand"] == "Dretec"
        assert result.metadata["model_code"] == "CS50A"

    def test_jiabao_brand(self):
        parser = RenphoParser()
        ad = _make_ad(local_name="JiaBao-CS50A")
        result = parser.parse(ad)
        assert result.metadata["brand"] == "JiaBao"

    def test_qn_scale_default_brand(self):
        parser = RenphoParser()
        ad = _make_ad(local_name="QN-Scale")
        result = parser.parse(ad)
        assert result.metadata["brand"] == "Qingniu"

    def test_qn_scale1_distinct_from_qn_scale(self):
        parser = RenphoParser()
        ad = _make_ad(local_name="QN-Scale1")
        result = parser.parse(ad)
        assert result.metadata["name_prefix"] == "QN-Scale1"

    def test_service_uuid_match(self):
        parser = RenphoParser()
        ad = _make_ad(service_uuids=["fff0"])
        result = parser.parse(ad)
        assert result is not None

    def test_service_uuid_181d(self):
        parser = RenphoParser()
        ad = _make_ad(service_uuids=["0000181d-0000-1000-8000-00805f9b34fb"])
        result = parser.parse(ad)
        assert result is not None


class TestRenphoGenericUuidGating:
    """A bare generic 16-bit UUID must not out-claim an explicit foreign CID.

    `fff0` / `ffe0` / `abf0` are generic Chinese-module service UUIDs shared
    with unrelated vendors (e.g. the iTENS TENS unit advertises `fff0` under
    company ID 0x3045). A UUID-only hit that is contradicted by a foreign
    manufacturer company ID is not a Qingniu scale.
    """

    def test_generic_uuid_with_foreign_cid_is_rejected(self):
        # iTENS shape: CID 0x3045 (raw `45 30` LE) + fff0/ffb0.
        ad = _make_ad(
            manufacturer_data=bytes.fromhex("4530") + b"EM12345",
            service_uuids=["fff0", "ffb0"],
        )
        assert RenphoParser().parse(ad) is None

    def test_generic_uuid_without_manufacturer_data_still_matches(self):
        ad = _make_ad(service_uuids=["fff0"])
        assert RenphoParser().parse(ad) is not None

    def test_catalog_name_survives_a_foreign_cid(self):
        ad = _make_ad(
            local_name="Yolanda-CS20H",
            manufacturer_data=bytes.fromhex("4530") + b"\x01",
            service_uuids=["fff0"],
        )
        result = RenphoParser().parse(ad)
        assert result is not None
        assert result.metadata["brand"] == "Yolanda"

    def test_own_cid_still_matches_with_generic_uuid(self):
        ad = _make_ad(
            manufacturer_data=struct.pack("<H", 0x06D0) + b"\x00\x00\x10",
            service_uuids=["fff0"],
        )
        assert RenphoParser().parse(ad) is not None


class TestRenphoDoesNotClaimHuamiCid:
    """CID 0x0157 is SIG-assigned to Anhui Huami (Zepp/Amazfit), not Qingniu.

    Bluetooth SIG Assigned Numbers, company_identifiers.yaml: 0x0157 =
    "Anhui Huami Information Technology Co., Ltd." (also adwatch's own
    _bt_company_ids.py). Every 0x0157 frame in the NearSight corpus is a
    Huami wearable (``57 01 02 ...``), so decoding a scale weight from it
    mislabels watches as scales.
    """

    HUAMI_FRAMES = [
        "570102ffffffffffffffffffffffffffffffff03d36a75af9292",
        "5701020202000304fcf6ffffffffffffffffff03f96690d95c10",
        "570101a701ff",
    ]

    @pytest.mark.parametrize("hexframe", HUAMI_FRAMES)
    def test_huami_corpus_frame_is_not_a_scale(self, hexframe):
        ad = _make_ad(manufacturer_data=bytes.fromhex(hexframe))
        assert RenphoParser().parse(ad) is None

    def test_0x0157_not_registered(self):
        from adwatch.registry import _default_registry
        entries = [e for e in _default_registry.get_entries() if e["name"] == "renpho"]
        assert entries, "renpho parser should be registered"
        cids = entries[0]["company_id"]
        cids = cids if isinstance(cids, (list, tuple)) else [cids]
        assert 0x0157 not in cids
        assert 0x06D0 in cids

    def test_huami_frame_yields_no_weight_even_with_scale_name(self):
        ad = _make_ad(
            local_name="QN-Scale",
            manufacturer_data=bytes.fromhex("5701c8001000665544332211"),
        )
        result = RenphoParser().parse(ad)
        assert result is not None  # the name still identifies the scale
        assert "weight_kg" not in result.metadata
        assert "embedded_mac" not in result.metadata
        assert "qingniu_cid" not in result.metadata
