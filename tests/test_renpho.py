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
    """v2.0.0: full Qingniu OEM brand catalog + 0x0157 CID + live weight."""

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

    def test_qingniu_cid_match(self):
        parser = RenphoParser()
        mfr = struct.pack("<H", 0x0157) + b"\xC8\x00\x10"  # 200 (=20.0 kg), kg, stable
        ad = _make_ad(manufacturer_data=mfr)
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["qingniu_cid"] is True
        assert result.metadata["weight_kg"] == 20.0
        assert result.metadata["unit"] == "kg"
        assert result.metadata["stable"] is True

    def test_qingniu_cid_lb_unstable(self):
        parser = RenphoParser()
        mfr = struct.pack("<H", 0x0157) + b"\x10\x27\x01"  # 10000 (=1000.0), lb, unstable
        ad = _make_ad(manufacturer_data=mfr)
        result = parser.parse(ad)
        assert result.metadata["unit"] == "lb"
        assert result.metadata["stable"] is False

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

    def test_embedded_mac_used_for_identity(self):
        parser = RenphoParser()
        # 4 reserved/header bytes then 6-byte MAC
        mfr = struct.pack("<H", 0x0157) + b"\x00\x00\x10\x00" + b"\x66\x55\x44\x33\x22\x11"
        ad = _make_ad(manufacturer_data=mfr, mac_address="AA:AA:AA:AA:AA:AA")
        result = parser.parse(ad)
        assert result.metadata.get("embedded_mac") == "11:22:33:44:55:66"
        expected = hashlib.sha256(b"renpho:11:22:33:44:55:66").hexdigest()[:16]
        assert result.identifier_hash == expected
