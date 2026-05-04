"""Tests for Nanoleaf HomeKit/HAP + mfr-data plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.nanoleaf import (
    NanoleafParser,
    APPLE_COMPANY_ID,
    NANOLEAF_COMPANY_ID,
    HAP_AD_TYPE,
)


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


def _register(registry):
    @register_parser(
        name="nanoleaf",
        company_id=(APPLE_COMPANY_ID, NANOLEAF_COMPANY_ID),
        local_name_pattern=r"^(Shapes|Canvas|NLM\d|NL1D|Nanoleaf)",
        description="Nanoleaf",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(NanoleafParser):
        pass

    return _P


def _hap_mfr(category=0x0005, gsn=42, aai=b"\x11\x22\x33\x44\x55\x66",
             config_number=1, compatible_version=2):
    """Build Apple HAP mfr-data: CID 004C + 14-byte HAP payload."""
    cid = struct.pack("<H", APPLE_COMPANY_ID)
    payload = bytes([
        HAP_AD_TYPE,
        (1 << 5) | 0x0D,  # AD version=1, length=13
    ]) + struct.pack("<H", category) + struct.pack("<H", gsn) + aai + bytes([
        config_number, compatible_version,
    ])
    return cid + payload


def _nanoleaf_mfr(payload=b"\x01\x02\x03"):
    return struct.pack("<H", NANOLEAF_COMPANY_ID) + payload


class TestNanoleafMatching:
    def test_match_nanoleaf_cid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=_nanoleaf_mfr())
        assert len(registry.match(ad)) == 1

    def test_match_apple_cid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=_hap_mfr())
        assert len(registry.match(ad)) == 1

    def test_match_name_shapes(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="Shapes ABC")
        assert len(registry.match(ad)) == 1


class TestHapDecode:
    def _parse(self, **kw):
        return NanoleafParser().parse(_make_ad(**kw))

    def test_hap_aai_extracted(self):
        result = self._parse(manufacturer_data=_hap_mfr(aai=b"\xaa\xbb\xcc\xdd\xee\xff"))
        assert result.metadata["hap_aai"] == "AA:BB:CC:DD:EE:FF"

    def test_hap_category_lightbulb(self):
        result = self._parse(manufacturer_data=_hap_mfr(category=0x0005))
        assert result.metadata["hap_category"] == "Lightbulb"
        assert result.metadata["hap_category_code"] == 0x0005

    def test_hap_gsn_extracted(self):
        result = self._parse(manufacturer_data=_hap_mfr(gsn=12345))
        assert result.metadata["hap_gsn"] == 12345

    def test_apple_cid_without_hap_byte_returns_none(self):
        # Apple CID but first payload byte != 0x06 → not a HAP advert
        cid = struct.pack("<H", APPLE_COMPANY_ID)
        ad = _make_ad(manufacturer_data=cid + b"\x10\x05")  # 0x10 = iBeacon
        assert self._parse(manufacturer_data=cid + b"\x10\x05") is None


class TestNanoleafName:
    def test_canvas_family(self):
        result = NanoleafParser().parse(_make_ad(local_name="Canvas Living"))
        assert result.metadata["model_family"] == "Canvas"

    def test_essentials_family(self):
        result = NanoleafParser().parse(_make_ad(local_name="NLM0 Bulb"))
        assert result.metadata["model_family"] == "Essentials"

    def test_nl1d_family(self):
        result = NanoleafParser().parse(_make_ad(local_name="NL1D"))
        assert result.metadata["model_family"] == "NL1D"


class TestNanoleafIdentity:
    def test_identity_uses_aai_when_present(self):
        ad = _make_ad(
            manufacturer_data=_hap_mfr(aai=b"\xde\xad\xbe\xef\x00\x11"),
            mac_address="11:22:33:44:55:66",
        )
        result = NanoleafParser().parse(ad)
        expected = hashlib.sha256(b"nanoleaf:DE:AD:BE:EF:00:11").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_returns_none_for_unrelated(self):
        assert NanoleafParser().parse(_make_ad(local_name="Other")) is None

    def test_parse_basics(self):
        result = NanoleafParser().parse(_make_ad(manufacturer_data=_nanoleaf_mfr()))
        assert result.parser_name == "nanoleaf"
        assert result.device_class == "light"
