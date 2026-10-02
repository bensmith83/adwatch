"""Tests for moonbird breathing-device plugin.

Per apk-ble-hunting/reports/moonbird-app_passive.md: mfr data = CID 0x0963
(wire 63 09) + 6-byte ASCII serial at full-mfr offsets 2-7.
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser
from adwatch.plugins.moonbird import MoonbirdParser, MOONBIRD_COMPANY_ID


def _ad(**kw):
    d = dict(timestamp="2026-01-01T00:00:00Z", mac_address="AA:BB:CC:DD:EE:02",
             address_type="random", manufacturer_data=None, service_data=None)
    d.update(kw)
    return RawAdvertisement(**d)


def _reg():
    r = ParserRegistry()

    @register_parser(name="moonbird", company_id=MOONBIRD_COMPANY_ID,
                     description="moonbird", version="1.0.0", core=False, registry=r)
    class _P(MoonbirdParser):
        pass
    return r


def test_company_id():
    assert MOONBIRD_COMPANY_ID == 0x0963


def test_wire_bytes_match_cid():
    # App checks hex prefix "6309" on the full mfr data (ble-plx includes CID)
    ad = _ad(manufacturer_data=bytes.fromhex("6309") + b"MB1234")
    assert ad.company_id == 0x0963
    assert len(_reg().match(ad)) == 1


def test_serial_decode_and_identity():
    ad = _ad(manufacturer_data=bytes.fromhex("6309") + b"AB12CD")
    r = MoonbirdParser().parse(ad)
    assert r.parser_name == "moonbird"
    assert r.metadata["serial_number"] == "AB12CD"
    assert r.identifier_hash == hashlib.sha256(b"moonbird:AB12CD").hexdigest()[:16]


def test_trailing_bytes_ignored_but_recorded():
    ad = _ad(manufacturer_data=bytes.fromhex("6309") + b"AB12CD" + b"\x01\x02")
    r = MoonbirdParser().parse(ad)
    assert r.metadata["serial_number"] == "AB12CD"
    assert r.metadata["trailing_hex"] == "0102"


def test_short_payload_falls_back_to_mac():
    ad = _ad(manufacturer_data=bytes.fromhex("6309") + b"AB")
    r = MoonbirdParser().parse(ad)
    assert "serial_number" not in r.metadata
    assert r.identifier_hash == hashlib.sha256(
        b"moonbird:AA:BB:CC:DD:EE:02").hexdigest()[:16]


def test_non_ascii_serial_not_decoded_as_text():
    ad = _ad(manufacturer_data=bytes.fromhex("6309") + bytes([0xff] * 6))
    r = MoonbirdParser().parse(ad)
    assert "serial_number" not in r.metadata
    assert r.metadata["serial_hex"] == "ffffffffffff"


def test_wrong_cid_returns_none():
    assert MoonbirdParser().parse(_ad(manufacturer_data=b"\x59\x00ABCDEF")) is None
    assert MoonbirdParser().parse(_ad()) is None
