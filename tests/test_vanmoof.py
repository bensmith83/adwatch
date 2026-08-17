"""Tests for VanMoof e-bike plugin.

Per apk-ble-hunting/reports/vanmoof-app_passive.md.
"""

import hashlib
import struct

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.vanmoof import (
    VanMoofParser,
    VANMOOF_SERVICE_UUIDS,
    VANMOOF_SHORT_UUID,
    VANMOOF_FAMILY_UUIDS,
    VANMOOF_COMPANY_ID,
    VANMOOF_NAME_PATTERN,
    TI_OAD_UUID,
)


def _make_ad(**kwargs):
    defaults = {
        "timestamp": "2026-08-16T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "public",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(
        name="vanmoof",
        company_id=VANMOOF_COMPANY_ID,
        service_uuid=VANMOOF_SERVICE_UUIDS,
        local_name_pattern=VANMOOF_NAME_PATTERN,
        description="VanMoof",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(VanMoofParser):
        pass

    return registry


class TestMatching:
    def test_matches_short_uuid(self):
        reg = _register(ParserRegistry())
        assert len(reg.match(_make_ad(service_uuids=[VANMOOF_SHORT_UUID]))) == 1

    def test_matches_family_uuid(self):
        reg = _register(ParserRegistry())
        ad = _make_ad(service_uuids=["6acb5500-e631-4069-944d-b8ca7598ad50"])
        assert len(reg.match(ad)) == 1

    def test_matches_name(self):
        reg = _register(ParserRegistry())
        assert len(reg.match(_make_ad(local_name="VANMOOF-S3-A1B2C"))) == 1

    def test_matches_company_id(self):
        reg = _register(ParserRegistry())
        ad = _make_ad(manufacturer_data=struct.pack("<H", VANMOOF_COMPANY_ID) + b"\x01")
        assert len(reg.match(ad)) == 1

    def test_ignores_unrelated(self):
        reg = _register(ParserRegistry())
        assert reg.match(_make_ad(service_uuids=["fd6f"], local_name="Moofer")) == []


class TestNameDecode:
    def test_electrified_name_gives_model_and_frame(self):
        r = VanMoofParser().parse(_make_ad(local_name="VANMOOF-S3-A1B2C"))
        assert r is not None
        assert r.metadata["model"] == "S3"
        assert r.metadata["frame_number"] == "A1B2C"
        assert r.device_class == "vehicle"

    def test_smartbike_name_gives_frame(self):
        r = VanMoofParser().parse(_make_ad(local_name="VanMoof BL-12345"))
        assert r.metadata["frame_number"] == "12345"
        assert r.metadata["model"] == "SmartBike"

    def test_name_without_frame_still_matches(self):
        r = VanMoofParser().parse(_make_ad(local_name="VANMOOF"))
        assert r is not None
        assert "frame_number" not in r.metadata


class TestUuidDecode:
    def test_family_uuid_maps_to_generation(self):
        for uuid, generation in VANMOOF_FAMILY_UUIDS.items():
            r = VanMoofParser().parse(_make_ad(service_uuids=[uuid]))
            assert r is not None
            assert r.metadata["generation"] == generation

    def test_short_uuid_marks_electrified_line(self):
        r = VanMoofParser().parse(_make_ad(service_uuids=[VANMOOF_SHORT_UUID]))
        assert r.metadata["generation"] == "Electrified (modern)"

    def test_ti_oad_alongside_vanmoof_flags_dfu(self):
        r = VanMoofParser().parse(
            _make_ad(service_uuids=[VANMOOF_SHORT_UUID, TI_OAD_UUID])
        )
        assert r.metadata["dfu_mode"] is True

    def test_ti_oad_alone_is_not_vanmoof(self):
        assert VanMoofParser().parse(_make_ad(service_uuids=[TI_OAD_UUID])) is None


class TestIdentity:
    def test_frame_number_beats_mac(self):
        p = VanMoofParser()
        a = _make_ad(mac_address="11:22:33:44:55:66", local_name="VANMOOF-S3-A1B2C")
        b = _make_ad(mac_address="99:88:77:66:55:44", local_name="VANMOOF-S3-A1B2C")
        assert p.parse(a).identifier_hash == p.parse(b).identifier_hash
        assert p.parse(a).identifier_hash == hashlib.sha256(
            b"vanmoof:A1B2C").hexdigest()[:16]

    def test_mac_fallback(self):
        r = VanMoofParser().parse(_make_ad(service_uuids=[VANMOOF_SHORT_UUID]))
        assert r.identifier_hash == hashlib.sha256(
            b"vanmoof:AA:BB:CC:DD:EE:FF").hexdigest()[:16]

    def test_returns_none_for_unrelated(self):
        assert VanMoofParser().parse(_make_ad(service_uuids=["fd6f"])) is None
