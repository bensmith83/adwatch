"""Tests for Bird shared-scooter plugin.

Per apk-ble-hunting/reports/bird-android_passive.md.
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.bird_scooter import (
    BirdScooterParser,
    BIRD_SERVICE_UUID,
    BIRD_NAME_PATTERN,
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
        name="bird_scooter",
        service_uuid=BIRD_SERVICE_UUID,
        local_name_pattern=BIRD_NAME_PATTERN,
        description="Bird",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(BirdScooterParser):
        pass

    return registry


class TestMatching:
    def test_matches_short_service_uuid(self):
        reg = _register(ParserRegistry())
        assert len(reg.match(_make_ad(service_uuids=["b13d"]))) == 1

    def test_matches_full_service_uuid(self):
        reg = _register(ParserRegistry())
        ad = _make_ad(service_uuids=["0000b13d-0000-1000-8000-00805f9b34fb"])
        assert len(reg.match(ad)) == 1

    def test_matches_name_only(self):
        reg = _register(ParserRegistry())
        assert len(reg.match(_make_ad(local_name="Bird-1A2B"))) == 1

    def test_ignores_unrelated(self):
        reg = _register(ParserRegistry())
        assert reg.match(_make_ad(service_uuids=["fd6f"], local_name="Birdhouse")) == []


class TestParsing:
    def test_uuid_advert_presence(self):
        r = BirdScooterParser().parse(_make_ad(service_uuids=["b13d"]))
        assert r is not None
        assert r.parser_name == "bird_scooter"
        assert r.device_class == "vehicle"
        assert r.metadata["vendor"] == "Bird"
        assert r.metadata["has_bird_service_uuid"] is True

    def test_name_carries_unit_id(self):
        r = BirdScooterParser().parse(
            _make_ad(service_uuids=["b13d"], local_name="Bird-4F7C")
        )
        assert r.metadata["device_name"] == "Bird-4F7C"
        assert r.metadata["unit_id"] == "4F7C"

    def test_identity_prefers_name_over_mac(self):
        p = BirdScooterParser()
        a = _make_ad(mac_address="11:22:33:44:55:66",
                     service_uuids=["b13d"], local_name="Bird-4F7C")
        b = _make_ad(mac_address="99:88:77:66:55:44",
                     service_uuids=["b13d"], local_name="Bird-4F7C")
        assert p.parse(a).identifier_hash == p.parse(b).identifier_hash
        assert p.parse(a).identifier_hash == hashlib.sha256(
            b"bird:Bird-4F7C").hexdigest()[:16]

    def test_identity_falls_back_to_mac(self):
        r = BirdScooterParser().parse(_make_ad(service_uuids=["b13d"]))
        assert r.identifier_hash == hashlib.sha256(
            b"bird:AA:BB:CC:DD:EE:FF").hexdigest()[:16]

    def test_manufacturer_payload_logged_not_decoded(self):
        # Byte layout is server-side only — we surface the raw bytes verbatim.
        data = bytes.fromhex("4c000102030405")
        r = BirdScooterParser().parse(_make_ad(service_uuids=["b13d"],
                                               manufacturer_data=data))
        assert r.raw_payload_hex == data.hex()
        assert r.metadata["manufacturer_payload_hex"] == "0102030405"
        assert r.metadata["payload_decode"] == "server_side_only"

    def test_rejects_unrelated_advert(self):
        assert BirdScooterParser().parse(
            _make_ad(service_uuids=["fd6f"], local_name="Blackbird")) is None
