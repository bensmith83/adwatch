"""Tests for the GN ReSound hearing-aid plugin.

Per apk-ble-hunting/reports/resound-smart3d_passive.md the APK itself is opaque
(Xamarin/.NET assemblies inside libmonodroid_bundle_app.so), so matching uses
vendor-specific public signals only:

  - GN Hearing SIG company IDs 0x0067 / 0x0089
  - a `ReSound` name token

The Google ASHA UUID 0xFDF0 is vendor-agnostic (every ASHA hearing aid
advertises it) and is deliberately NOT a match criterion — `plugins/oticon.py`
already owns the generic-ASHA presence record. When a ReSound signal is present,
the spec-defined ASHA service data is decoded as enrichment.
"""

import hashlib
import struct

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.resound import (
    ReSoundParser,
    GN_HEARING_COMPANY_IDS,
    ASHA_SERVICE_UUID,
    decode_asha_service_data,
)


def _make_ad(**kwargs):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "random",
        "manufacturer_data": None,
        "service_data": None,
        "local_name": "ReSound LiNX Quattro",
    }
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _asha(version=0x01, capabilities=0x00, hisync=b"\xde\xad\xbe\xef") -> dict:
    return {ASHA_SERVICE_UUID: bytes([version, capabilities]) + hisync}


def _register(registry):
    @register_parser(
        name="resound",
        company_id=list(GN_HEARING_COMPANY_IDS),
        local_name_pattern=r"(?i)re[\s-]?sound",
        description="ReSound",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(ReSoundParser):
        pass

    return _P


class TestReSoundConstants:
    def test_gn_hearing_company_ids(self):
        assert set(GN_HEARING_COMPANY_IDS) == {0x0067, 0x0089}

    def test_asha_uuid(self):
        assert ASHA_SERVICE_UUID == "fdf0"


class TestAshaServiceData:
    def test_decode_left_monaural(self):
        decoded = decode_asha_service_data(b"\x01\x00\xde\xad\xbe\xef")
        assert decoded["asha_protocol_version"] == 1
        assert decoded["side"] == "left"
        assert decoded["binaural"] is False
        assert decoded["hi_sync_id"] == "deadbeef"

    def test_decode_right_binaural(self):
        decoded = decode_asha_service_data(b"\x01\x03\x00\x11\x22\x33")
        assert decoded["side"] == "right"
        assert decoded["binaural"] is True
        assert decoded["hi_sync_id"] == "00112233"

    def test_short_payload_partial_decode(self):
        decoded = decode_asha_service_data(b"\x01\x02")
        assert decoded["asha_protocol_version"] == 1
        assert decoded["side"] == "left"
        assert "hi_sync_id" not in decoded

    def test_empty_payload(self):
        assert decode_asha_service_data(b"") == {}


class TestReSoundMatching:
    def test_match_company_id_0067(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name=None,
                      manufacturer_data=struct.pack("<H", 0x0067) + b"\x01")
        assert len(registry.match(ad)) == 1

    def test_match_company_id_0089(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name=None,
                      manufacturer_data=struct.pack("<H", 0x0089) + b"\x01")
        assert len(registry.match(ad)) == 1

    def test_match_name(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(local_name="GN ReSound"))) == 1

    def test_asha_uuid_alone_does_not_match(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="Hearing Aid", service_uuids=[ASHA_SERVICE_UUID],
                      service_data=_asha())
        assert registry.match(ad) == []


class TestReSoundParse:
    def test_name_match(self):
        result = ReSoundParser().parse(_make_ad(local_name="ReSound LiNX Quattro"))
        assert result is not None
        assert result.parser_name == "resound"
        assert result.device_class == "hearing_aid"
        assert result.metadata["vendor"] == "GN Hearing"
        assert result.metadata["device_name"] == "ReSound LiNX Quattro"

    def test_company_id_match(self):
        result = ReSoundParser().parse(
            _make_ad(local_name=None,
                     manufacturer_data=struct.pack("<H", 0x0067) + b"\xaa\xbb")
        )
        assert result is not None
        assert result.metadata["cid_match"] is True
        assert result.metadata["payload_hex"] == "aabb"

    def test_asha_enrichment_when_vendor_confirmed(self):
        result = ReSoundParser().parse(_make_ad(service_data=_asha(capabilities=0x03)))
        assert result.metadata["asha_compliant"] is True
        assert result.metadata["side"] == "right"
        assert result.metadata["binaural"] is True
        assert result.metadata["hi_sync_id"] == "deadbeef"

    def test_asha_alone_returns_none(self):
        assert ReSoundParser().parse(
            _make_ad(local_name="Some Aid", service_data=_asha())
        ) is None

    def test_identity_prefers_hisync_and_side(self):
        result = ReSoundParser().parse(_make_ad(service_data=_asha(capabilities=0x01)))
        expected = hashlib.sha256(b"resound:deadbeef:right").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_pair_members_differ(self):
        left = ReSoundParser().parse(_make_ad(service_data=_asha(capabilities=0x00)))
        right = ReSoundParser().parse(_make_ad(service_data=_asha(capabilities=0x01)))
        assert left.identifier_hash != right.identifier_hash

    def test_identity_falls_back_to_mac(self):
        result = ReSoundParser().parse(_make_ad())
        expected = hashlib.sha256(b"resound:AA:BB:CC:DD:EE:FF").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_no_asha_no_claims(self):
        result = ReSoundParser().parse(_make_ad())
        assert "asha_compliant" not in result.metadata
        assert "hi_sync_id" not in result.metadata

    def test_unrelated_returns_none(self):
        assert ReSoundParser().parse(
            _make_ad(local_name="Oticon More 1 L",
                     manufacturer_data=struct.pack("<H", 0x01D7) + b"\x00")
        ) is None


class TestReSoundDoesNotDoubleClaimWithOticon:
    """oticon.py emits a generic "uncertain" record for any ASHA hearing aid.
    When the advert already attributes the device to GN Hearing/ReSound, that
    generic record must stand down so only `resound` claims the sighting."""

    def test_oticon_skips_resound_name(self):
        from adwatch.plugins.oticon import OticonParser
        ad = _make_ad(local_name="ReSound LiNX Quattro",
                      service_uuids=[ASHA_SERVICE_UUID], service_data=_asha())
        assert OticonParser().parse(ad) is None

    def test_oticon_skips_gn_hearing_company_id(self):
        from adwatch.plugins.oticon import OticonParser
        ad = _make_ad(local_name=None, service_uuids=[ASHA_SERVICE_UUID],
                      manufacturer_data=struct.pack("<H", 0x0089) + b"\x01")
        assert OticonParser().parse(ad) is None

    def test_oticon_still_claims_generic_asha(self):
        from adwatch.plugins.oticon import OticonParser
        ad = _make_ad(local_name="Hearing Aid", service_uuids=[ASHA_SERVICE_UUID])
        result = OticonParser().parse(ad)
        assert result is not None
        assert result.metadata["vendor_attribution"] == "uncertain"

    def test_oticon_still_claims_its_own_devices(self):
        from adwatch.plugins.oticon import OticonParser
        ad = _make_ad(local_name="Oticon More1 L", service_uuids=[ASHA_SERVICE_UUID])
        result = OticonParser().parse(ad)
        assert result is not None
        assert result.metadata["vendor_attribution"] == "oticon"
