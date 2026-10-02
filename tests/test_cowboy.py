"""Tests for Cowboy e-bike presence plugin.

Per apk-ble-hunting/reports/cowboy-app_passive.md: vendor 128-bit service UUID
C0B0A000-18EB-499D-B266-2F2910744274 is the only fingerprint; no mfr/service
data telemetry is broadcast.
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser
from adwatch.plugins.cowboy import CowboyParser, COWBOY_SERVICE_UUID

UUID = "c0b0a000-18eb-499d-b266-2f2910744274"


def _make_ad(**kw):
    d = dict(timestamp="2026-10-01T00:00:00Z", mac_address="C1:22:33:44:55:66",
             address_type="random", manufacturer_data=None, service_data=None)
    d.update(kw)
    return RawAdvertisement(**d)


def _register(registry):
    @register_parser(name="cowboy", service_uuid=COWBOY_SERVICE_UUID,
                     description="Cowboy", version="1.0.0", core=False,
                     registry=registry)
    class _P(CowboyParser):
        pass
    return _P


def test_constant():
    assert COWBOY_SERVICE_UUID == UUID


def test_matches_uppercase_uuid():
    reg = ParserRegistry()
    _register(reg)
    ad = _make_ad(service_uuids=[UUID.upper()])
    assert len(reg.match(ad)) == 1


def test_no_match_other_uuid():
    reg = ParserRegistry()
    _register(reg)
    ad = _make_ad(service_uuids=["c0b0a001-18eb-499d-b266-2f2910744274"],
                  local_name="Cowboy")
    assert reg.match(ad) == []


def test_parse_presence():
    ad = _make_ad(service_uuids=[UUID], local_name="My Bike")
    r = CowboyParser().parse(ad)
    assert r is not None
    assert r.parser_name == "cowboy"
    assert r.device_class == "vehicle"
    assert r.metadata["vendor"] == "Cowboy"
    assert r.metadata["device_name"] == "My Bike"
    assert r.metadata["telemetry"].startswith("none")
    assert r.identifier_hash == hashlib.sha256(
        b"cowboy:C1:22:33:44:55:66").hexdigest()[:16]


def test_parse_rejects_without_uuid():
    assert CowboyParser().parse(_make_ad(local_name="Cowboy")) is None


def test_default_registry_has_cowboy():
    from adwatch.registry import _default_registry
    import adwatch.plugins.cowboy  # noqa: F401
    names = [p.name for p in _default_registry.get_all()]
    assert "cowboy" in names
