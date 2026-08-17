"""Tests for Shearwater dive computer plugin.

Per apk-ble-hunting/reports/shearwater-cloud_passive.md.
"""

import hashlib
import struct

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.shearwater import (
    ShearwaterParser,
    SHEARWATER_COMPANY_ID,
    SHEARWATER_MODELS,
    SHEARWATER_NAME_PATTERN,
    SHEARWATER_SERVICE_UUIDS,
    DCCP2_UUID,
    SHEARWATER_MAC_PREFIXES,
)


def _make_ad(**kwargs):
    defaults = {
        "timestamp": "2026-08-16T00:00:00Z",
        "mac_address": "10:AA:BB:CC:DD:EE",
        "address_type": "public",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(
        name="shearwater",
        company_id=SHEARWATER_COMPANY_ID,
        service_uuid=SHEARWATER_SERVICE_UUIDS,
        local_name_pattern=SHEARWATER_NAME_PATTERN,
        description="Shearwater",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(ShearwaterParser):
        pass

    return registry


class TestMatching:
    def test_company_id_is_shearwater_research(self):
        assert SHEARWATER_COMPANY_ID == 0x1064

    def test_every_allow_list_name_matches(self):
        reg = _register(ParserRegistry())
        for name in SHEARWATER_MODELS:
            assert len(reg.match(_make_ad(local_name=name))) == 1, name

    def test_matches_dccp_service_uuid(self):
        reg = _register(ParserRegistry())
        assert len(reg.match(_make_ad(service_uuids=[DCCP2_UUID]))) == 1

    def test_matches_company_id(self):
        reg = _register(ParserRegistry())
        ad = _make_ad(manufacturer_data=struct.pack("<H", SHEARWATER_COMPANY_ID) + b"\x01")
        assert len(reg.match(ad)) == 1

    def test_partial_name_does_not_match(self):
        reg = _register(ParserRegistry())
        for name in ("Petrel Pro", "My Teric", "Perdixy", "Peregrine Falcon"):
            assert reg.match(_make_ad(local_name=name)) == [], name

    def test_mac_prefix_alone_does_not_match(self):
        # The `10`/`13` prefix is far too broad to register on — it would claim
        # any nameless device in that address space.
        reg = _register(ParserRegistry())
        assert reg.match(_make_ad(mac_address="10:11:22:33:44:55")) == []


class TestParsing:
    def test_model_and_family(self):
        r = ShearwaterParser().parse(_make_ad(local_name="Perdix AI"))
        assert r is not None
        assert r.parser_name == "shearwater"
        assert r.device_class == "sensor"
        assert r.metadata["model"] == "Perdix AI"
        assert r.metadata["model_family"] == "Perdix"
        assert r.metadata["vendor"] == "Shearwater"

    def test_all_models_resolve_a_family(self):
        p = ShearwaterParser()
        for name, family in SHEARWATER_MODELS.items():
            r = p.parse(_make_ad(local_name=name))
            assert r.metadata["model_family"] == family, name

    def test_mac_prefix_flagged_as_corroborating(self):
        p = ShearwaterParser()
        hit = p.parse(_make_ad(local_name="Teric", mac_address="13:01:02:03:04:05"))
        assert hit.metadata["mac_prefix_match"] is True
        miss = p.parse(_make_ad(local_name="Teric", mac_address="C0:01:02:03:04:05"))
        assert miss.metadata["mac_prefix_match"] is False

    def test_mac_prefix_requires_public_address(self):
        r = ShearwaterParser().parse(
            _make_ad(local_name="Teric", mac_address="10:01:02:03:04:05",
                     address_type="random"))
        assert r.metadata["mac_prefix_match"] is False

    def test_prefixes_are_the_documented_pair(self):
        assert SHEARWATER_MAC_PREFIXES == ("10", "13")

    def test_service_uuid_only_advert(self):
        r = ShearwaterParser().parse(_make_ad(service_uuids=[DCCP2_UUID]))
        assert r is not None
        assert r.metadata["dccp_service"] == "DCCP2"
        assert "model" not in r.metadata

    def test_manufacturer_payload_logged(self):
        data = struct.pack("<H", SHEARWATER_COMPANY_ID) + bytes.fromhex("dead")
        r = ShearwaterParser().parse(_make_ad(local_name="Petrel 3", manufacturer_data=data))
        assert r.metadata["manufacturer_payload_hex"] == "dead"
        assert r.raw_payload_hex == data.hex()

    def test_no_telemetry_claimed(self):
        r = ShearwaterParser().parse(_make_ad(local_name="Petrel 2"))
        assert r.metadata["telemetry"] == "connect_required_dccp"

    def test_identity_is_mac_based(self):
        r = ShearwaterParser().parse(_make_ad(local_name="Teric",
                                              mac_address="10:AA:BB:CC:DD:EE"))
        assert r.identifier_hash == hashlib.sha256(
            b"shearwater:10:AA:BB:CC:DD:EE").hexdigest()[:16]

    def test_returns_none_for_unrelated(self):
        assert ShearwaterParser().parse(
            _make_ad(local_name="Petrel Pro", service_uuids=["fd6f"])) is None
