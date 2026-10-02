"""Tests for greenteg CORE body-temperature sensor plugin.

Per apk-ble-hunting/reports/greenteg-core-app_passive.md. Offsets in the report
are into getManufacturerSpecificData() SparseArray values (CID already
stripped), so they map directly onto adwatch manufacturer_payload[N].
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser
from adwatch.plugins.greenteg_core import (
    GreentegCoreParser, GREENTEG_APP_UUID, GREENTEG_BOOTLOADER_UUID,
)

APP = "00004200-f366-40b2-ac37-70cce0aa83b1"
BOOT = "00002100-5b1e-4347-b07c-97b514dae121"


def _ad(**kw):
    d = dict(timestamp="2026-01-01T00:00:00Z", mac_address="D0:11:22:33:44:55",
             address_type="public", manufacturer_data=None, service_data=None)
    d.update(kw)
    return RawAdvertisement(**d)


def _registry():
    reg = ParserRegistry()

    @register_parser(name="greenteg_core",
                     service_uuid=[GREENTEG_APP_UUID, GREENTEG_BOOTLOADER_UUID],
                     description="t", version="1", core=False, registry=reg)
    class _P(GreentegCoreParser):
        pass
    return reg


def test_uuid_constants():
    assert GREENTEG_APP_UUID == APP
    assert GREENTEG_BOOTLOADER_UUID == BOOT


def test_matches_both_uuids():
    reg = _registry()
    assert len(reg.match(_ad(service_uuids=[APP.upper()]))) == 1
    assert len(reg.match(_ad(service_uuids=[BOOT]))) == 1


def test_no_match_on_mfr_header_alone():
    # byte0==0x00 is too weak to claim on; must not match without the UUID.
    assert _registry().match(_ad(manufacturer_data=bytes.fromhex("ffff00211a92"))) == []


def test_full_advert_offset_pin():
    # Hand-built: CID 0xFFFF (unknown, captured live) + value 00 | 0x23 | 0x921A
    # value[1]=0x23 -> state = 3, bit5 worn = 1; temp = 0x921A = 37402 mC
    mfr = bytes([0xFF, 0xFF, 0x00, 0x23, 0x1A, 0x92])
    r = GreentegCoreParser().parse(_ad(service_uuids=[APP], manufacturer_data=mfr))
    m = r.metadata
    assert m["mode"] == "application"
    assert m["device_state_code"] == 3
    assert m["service_occupied"] is True
    assert m["core_temp_mC"] == 37402
    assert m["core_temp_c"] == 37.402
    assert m["core_temp_plausible"] is True
    assert m["company_id"] == 0xFFFF
    assert m["sensitive"] is True


def test_not_worn_and_tail_ignored():
    mfr = bytes([0x34, 0x12, 0x00, 0x01, 0x30, 0x75, 0xAA, 0xBB])  # 30000 mC
    m = GreentegCoreParser().parse(_ad(service_uuids=[APP], manufacturer_data=mfr)).metadata
    assert m["device_state_code"] == 1
    assert m["service_occupied"] is False
    assert m["core_temp_c"] == 30.0


def test_implausible_temp_flagged():
    mfr = bytes([0x34, 0x12, 0x00, 0x00, 0x10, 0x00])
    m = GreentegCoreParser().parse(_ad(service_uuids=[APP], manufacturer_data=mfr)).metadata
    assert m["core_temp_plausible"] is False


def test_bad_header_no_telemetry():
    mfr = bytes([0x34, 0x12, 0x01, 0x23, 0x1A, 0x92])
    m = GreentegCoreParser().parse(_ad(service_uuids=[APP], manufacturer_data=mfr)).metadata
    assert "core_temp_c" not in m


def test_short_payload_no_telemetry():
    mfr = bytes([0x34, 0x12, 0x00, 0x23, 0x1A])
    m = GreentegCoreParser().parse(_ad(service_uuids=[APP], manufacturer_data=mfr)).metadata
    assert "core_temp_c" not in m


def test_bootloader_mode_and_identity():
    r = GreentegCoreParser().parse(_ad(service_uuids=[BOOT]))
    assert r.metadata["mode"] == "bootloader"
    assert r.device_class == "wearable"
    assert r.identifier_hash == hashlib.sha256(b"greenteg_core:D0:11:22:33:44:55").hexdigest()[:16]


def test_rejects_without_uuid():
    assert GreentegCoreParser().parse(_ad(manufacturer_data=bytes([0, 0, 0, 0x23, 0x1A, 0x92]))) is None
