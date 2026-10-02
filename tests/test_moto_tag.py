"""Tests for Moto Tag owner-advert plugin.

Per apk-ble-hunting/reports/motorola-tag_passive.md: service data 0xFC7C,
exactly 1 byte: state=(b>>6)&3, sub_state=(b>>4)&3, uwb=(b>>3)&1,
category=(b>>1)&3, mode=b&1 (0=FMD, 1=SM). 0xFEAA (Eddystone/FMDN) is
generic and NOT claimed.
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser
from adwatch.plugins.moto_tag import MotoTagParser, MOTO_TAG_SERVICE_UUID

FULL = "0000fc7c-0000-1000-8000-00805f9b34fb"


def _make_ad(**kw):
    d = dict(timestamp="2026-10-01T00:00:00Z", mac_address="5A:11:22:33:44:55",
             address_type="random", manufacturer_data=None, service_data=None)
    d.update(kw)
    return RawAdvertisement(**d)


def _register(registry):
    @register_parser(name="moto_tag", service_uuid=MOTO_TAG_SERVICE_UUID,
                     description="Moto Tag", version="1.0.0", core=False,
                     registry=registry)
    class _P(MotoTagParser):
        pass
    return _P


def test_constant():
    assert MOTO_TAG_SERVICE_UUID == "fc7c"


def test_matches_service_data_key():
    reg = ParserRegistry()
    _register(reg)
    assert len(reg.match(_make_ad(service_data={FULL: b"\x01"}))) == 1


def test_feaa_only_not_matched():
    reg = ParserRegistry()
    _register(reg)
    ad = _make_ad(service_data={"feaa": bytes(21)})
    assert reg.match(ad) == []


def test_bitfield_decode_all_set_pattern():
    # 0b10_01_1_10_1 = 0x9D
    r = MotoTagParser().parse(_make_ad(service_data={"fc7c": b"\x9d"}))
    m = r.metadata
    assert m["state_code"] == 2
    assert m["sub_state"] == 1
    assert m["uwb_capable"] is True
    assert m["category_code"] == 2
    assert m["mode_code"] == 1
    assert m["mode"] == "SM"
    assert m["status_byte"] == 0x9D
    assert r.device_class == "tracker"
    assert r.parser_name == "moto_tag"


def test_mode_fmd_no_uwb():
    r = MotoTagParser().parse(_make_ad(service_data={FULL: b"\x40"}))
    assert r.metadata["mode"] == "FMD"
    assert r.metadata["uwb_capable"] is False
    assert r.metadata["state_code"] == 1


def test_full_advert_no_offset_shift():
    # Service data payload is used as-is (getServiceData -> no CID strip),
    # alongside an FMDN Eddystone frame.
    ad = _make_ad(service_data={FULL: bytes([0x09]),
                                "0000feaa-0000-1000-8000-00805f9b34fb": b"\x41" + bytes(20)})
    m = MotoTagParser().parse(ad).metadata
    assert m["uwb_capable"] is True and m["mode"] == "SM"
    assert m["fmdn_frame_seen"] is True


def test_wrong_length_rejected():
    p = MotoTagParser()
    assert p.parse(_make_ad(service_data={"fc7c": b""})) is None
    assert p.parse(_make_ad(service_data={"fc7c": b"\x01\x02"})) is None


def test_no_service_data_rejected():
    assert MotoTagParser().parse(_make_ad(service_uuids=["fc7c"])) is None


def test_identity_mac_based():
    r = MotoTagParser().parse(_make_ad(service_data={"fc7c": b"\x00"}))
    assert r.identifier_hash == hashlib.sha256(
        b"moto_tag:5A:11:22:33:44:55").hexdigest()[:16]


def test_default_registry_has_moto_tag():
    from adwatch.registry import _default_registry
    import adwatch.plugins.moto_tag  # noqa: F401
    assert "moto_tag" in [p.name for p in _default_registry.get_all()]
