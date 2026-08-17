"""Tests for Specialized Turbo (Mission Control) e-bike plugin.

Per apk-ble-hunting/reports/specialized-turbo_passive.md.
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.specialized_turbo import (
    SpecializedTurboParser,
    SCHEME_A_SUFFIX,
    SCHEME_B_SUFFIX,
    SPECIALIZED_SERVICE_UUIDS,
    SPECIALIZED_NAME_PATTERN,
    scheme_for_uuid,
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
        name="specialized_turbo",
        service_uuid=SPECIALIZED_SERVICE_UUIDS,
        local_name_pattern=SPECIALIZED_NAME_PATTERN,
        description="Specialized Turbo",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(SpecializedTurboParser):
        pass

    return registry


class TestSchemeDetection:
    def test_scheme_a_tail_is_gigatronik_reversed(self):
        assert bytes.fromhex(SCHEME_A_SUFFIX.replace("-", "")) == b"\x00\x00KINORTAGIG"

    def test_scheme_b_tail_is_turbohmi2017_reversed(self):
        assert bytes.fromhex(SCHEME_B_SUFFIX.replace("-", "")) == b"7102IMHOBRUT"

    def test_scheme_for_uuid_a(self):
        assert scheme_for_uuid("00000001-0000-4b49-4e4f-525441474947") == "gigatronik"

    def test_scheme_for_uuid_b(self):
        assert scheme_for_uuid("0000ff01-3731-3032-494d-484f42525554") == "turbo_hmi_2017"

    def test_scheme_for_uuid_none(self):
        assert scheme_for_uuid("0000fd6f-0000-1000-8000-00805f9b34fb") is None


class TestMatching:
    def test_matches_enumerated_scheme_a_uuid(self):
        reg = _register(ParserRegistry())
        ad = _make_ad(service_uuids=["00000001-0000-4b49-4e4f-525441474947"])
        assert len(reg.match(ad)) == 1

    def test_matches_enumerated_scheme_b_uuid(self):
        reg = _register(ParserRegistry())
        ad = _make_ad(service_uuids=["00000002-3731-3032-494d-484f42525554"])
        assert len(reg.match(ad)) == 1

    def test_matches_model_name(self):
        reg = _register(ParserRegistry())
        assert len(reg.match(_make_ad(local_name="Turbo Levo 4C7A21"))) == 1

    def test_ignores_unrelated(self):
        reg = _register(ParserRegistry())
        assert reg.match(_make_ad(service_uuids=["fd6f"], local_name="Turbotax")) == []


class TestParsing:
    def test_scheme_a_uuid_decoded(self):
        r = SpecializedTurboParser().parse(
            _make_ad(service_uuids=["00000001-0000-4b49-4e4f-525441474947"])
        )
        assert r is not None
        assert r.parser_name == "specialized_turbo"
        assert r.device_class == "vehicle"
        assert r.metadata["uuid_scheme"] == "gigatronik"
        assert r.metadata["service_slot"] == "0001"

    def test_unenumerated_slot_still_decodes_when_name_matched(self):
        # Registry match came from the name; parse() suffix-checks any slot.
        r = SpecializedTurboParser().parse(
            _make_ad(local_name="Levo SL 9F1C22",
                     service_uuids=["0000abcd-3731-3032-494d-484f42525554"])
        )
        assert r.metadata["uuid_scheme"] == "turbo_hmi_2017"
        assert r.metadata["service_slot"] == "abcd"

    def test_name_gives_model_and_serial(self):
        r = SpecializedTurboParser().parse(_make_ad(local_name="Turbo Levo 4C7A21"))
        assert r.metadata["model"] == "Turbo Levo"
        assert r.metadata["serial"] == "4C7A21"

    def test_name_without_serial(self):
        r = SpecializedTurboParser().parse(_make_ad(local_name="Kenevo"))
        assert r is not None
        assert "serial" not in r.metadata

    def test_identity_prefers_serial(self):
        p = SpecializedTurboParser()
        a = _make_ad(mac_address="11:22:33:44:55:66", local_name="Turbo Levo 4C7A21")
        b = _make_ad(mac_address="99:88:77:66:55:44", local_name="Turbo Levo 4C7A21")
        assert p.parse(a).identifier_hash == p.parse(b).identifier_hash
        assert p.parse(a).identifier_hash == hashlib.sha256(
            b"specialized:4C7A21").hexdigest()[:16]

    def test_identity_mac_fallback(self):
        r = SpecializedTurboParser().parse(
            _make_ad(service_uuids=["00000001-0000-4b49-4e4f-525441474947"])
        )
        assert r.identifier_hash == hashlib.sha256(
            b"specialized:AA:BB:CC:DD:EE:FF").hexdigest()[:16]

    def test_rejects_unrelated(self):
        assert SpecializedTurboParser().parse(
            _make_ad(service_uuids=["fd6f"], local_name="TurboX")) is None
