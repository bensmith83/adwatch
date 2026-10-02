"""Tests for Embr Wave 2 thermoregulation wristband plugin.

Per apk-ble-hunting/reports/embrlabs-eden_passive.md: presence-only via the
advertised vendor 128-bit service UUID.
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser
from adwatch.plugins.embr_wave import EmbrWaveParser, EMBR_SERVICE_UUID

UUID = "00002001-1112-efde-1523-725a2aab0123"


def _ad(**kw):
    d = dict(timestamp="2026-01-01T00:00:00Z", mac_address="C0:11:22:33:44:55",
             address_type="random", manufacturer_data=None, service_data=None)
    d.update(kw)
    return RawAdvertisement(**d)


def _registry():
    reg = ParserRegistry()

    @register_parser(name="embr_wave", service_uuid=EMBR_SERVICE_UUID,
                     description="t", version="1", core=False, registry=reg)
    class _P(EmbrWaveParser):
        pass
    return reg


def test_uuid_constant():
    assert EMBR_SERVICE_UUID == UUID


def test_matches_uuid_uppercase():
    assert len(_registry().match(_ad(service_uuids=[UUID.upper()]))) == 1


def test_no_match_nordic_dfu_alone():
    assert _registry().match(_ad(service_uuids=["0000fe59-0000-1000-8000-00805f9b34fb"])) == []


def test_parse():
    r = EmbrWaveParser().parse(_ad(service_uuids=[UUID], local_name="Wave"))
    assert r.parser_name == "embr_wave"
    assert r.device_class == "wearable"
    assert r.identifier_hash == hashlib.sha256(b"embrwave:C0:11:22:33:44:55").hexdigest()[:16]
    assert r.metadata["mode"] == "app"
    assert r.metadata["device_name"] == "Wave"
    assert r.metadata["sensitive"] is True


def test_parse_rejects_without_uuid():
    assert EmbrWaveParser().parse(_ad(service_uuids=["180f"])) is None
