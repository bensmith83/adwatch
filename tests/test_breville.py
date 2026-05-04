"""Tests for Breville / ChefSteps Joule plugin."""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.breville import (
    BrevilleParser,
    BREVILLE_MODERN_CID,
    BREVILLE_LEGACY_CID,
    JOULE_SERVICE_UUID,
)


def _make_ad(**kw):
    defaults = {"timestamp": "2025-01-01T00:00:00Z", "mac_address": "AA:BB:CC:DD:EE:FF",
                "address_type": "random", "manufacturer_data": None, "service_data": None}
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(name="breville",
                     company_id=[BREVILLE_MODERN_CID, BREVILLE_LEGACY_CID],
                     service_uuid=JOULE_SERVICE_UUID,
                     description="Breville", version="1.0.0", core=False,
                     registry=registry)
    class _P(BrevilleParser):
        pass
    return _P


def _modern_mfr(version=0x01, model=0x03, unique=b"\xde\xad\xbe\xef", tail=b""):
    """Build modern Breville 0x0955 mfr-data."""
    cid = (BREVILLE_MODERN_CID).to_bytes(2, "little")
    return cid + bytes([version, model, version]) + unique + tail


def _joule_mfr(type_byte=0x10, variant=b"\x18\x17\x20"):
    """Build legacy Joule 0x0159 mfr-data per chefsteps fixtures."""
    cid = (BREVILLE_LEGACY_CID).to_bytes(2, "little")
    family = bytes.fromhex("a0a35db7e1")
    return cid + bytes([type_byte]) + family + variant


class TestBrevilleMatching:
    def test_match_modern_cid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=_modern_mfr())
        assert len(registry.match(ad)) == 1

    def test_match_legacy_cid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=_joule_mfr())
        assert len(registry.match(ad)) == 1

    def test_match_joule_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[JOULE_SERVICE_UUID])
        assert len(registry.match(ad)) == 1


class TestModernBrevilleParsing:
    def test_decodes_model_byte(self):
        ad = _make_ad(manufacturer_data=_modern_mfr(model=0x03))
        result = BrevilleParser().parse(ad)
        assert result is not None
        assert result.metadata["model_byte"] == 0x03
        assert result.metadata["model"] == "BES995"
        assert result.metadata["family"] == "modern"

    def test_lunar_model_byte(self):
        ad = _make_ad(manufacturer_data=_modern_mfr(model=0xFE))
        result = BrevilleParser().parse(ad)
        assert result.metadata["model"] == "LUNAR"

    def test_unique_id_hex(self):
        ad = _make_ad(manufacturer_data=_modern_mfr(unique=b"\xde\xad\xbe\xef"))
        result = BrevilleParser().parse(ad)
        assert result.metadata["unique_id"] == "DEADBEEF"

    def test_identity_uses_unique_id(self):
        ad = _make_ad(manufacturer_data=_modern_mfr(unique=b"\xca\xfe\xba\xbe"),
                      mac_address="11:22:33:44:55:66")
        result = BrevilleParser().parse(ad)
        expected = hashlib.sha256(b"breville:CAFEBABE").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_unknown_model_byte(self):
        ad = _make_ad(manufacturer_data=_modern_mfr(model=0x42))
        result = BrevilleParser().parse(ad)
        assert result.metadata["model_byte"] == 0x42
        assert result.metadata["model"].startswith("unknown")


class TestLegacyJouleParsing:
    def test_family_tag(self):
        ad = _make_ad(manufacturer_data=_joule_mfr())
        result = BrevilleParser().parse(ad)
        assert result is not None
        assert result.metadata["family"] == "joule_legacy"
        assert result.metadata["model"] == "Joule"

    def test_variant_extraction(self):
        ad = _make_ad(manufacturer_data=_joule_mfr(variant=b"\x77\x14\x85"))
        result = BrevilleParser().parse(ad)
        assert result.metadata["device_variant"] == "771485"

    def test_identity_uses_variant(self):
        ad = _make_ad(manufacturer_data=_joule_mfr(variant=b"\x12\x34\x56"),
                      mac_address="11:22:33:44:55:66")
        result = BrevilleParser().parse(ad)
        expected = hashlib.sha256(b"breville_joule:123456").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_uuid_only_match_no_variant(self):
        ad = _make_ad(service_uuids=[JOULE_SERVICE_UUID])
        result = BrevilleParser().parse(ad)
        assert result is not None
        assert result.metadata["family"] == "joule_legacy"

    def test_legacy_cid_with_wrong_prefix_still_returns_result(self):
        # Legacy CID without the joule family prefix — still tag as legacy
        # but no device_variant.
        cid = (BREVILLE_LEGACY_CID).to_bytes(2, "little")
        ad = _make_ad(manufacturer_data=cid + b"\x10\x00\x00")
        result = BrevilleParser().parse(ad)
        assert result is not None
        assert "device_variant" not in result.metadata


class TestBrevilleBasics:
    def test_returns_none_unrelated(self):
        ad = _make_ad(manufacturer_data=b"\x11\x22\x33\x44")
        assert BrevilleParser().parse(ad) is None

    def test_basics(self):
        ad = _make_ad(manufacturer_data=_modern_mfr())
        result = BrevilleParser().parse(ad)
        assert result.parser_name == "breville"
        assert result.beacon_type == "breville"
        assert result.device_class == "appliance"
