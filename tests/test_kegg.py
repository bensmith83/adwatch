"""Tests for kegg fertility / kegel trainer plugin.

Per apk-ble-hunting/reports/ladytechnologies-kegel_passive.md: name == "kegg";
app reads ABSOLUTE offsets 15-18 of ScanRecord.getBytes() (battery,
measurementStatus, deviceStatus, bufferCount). CID unknown.
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser
from adwatch.plugins.kegg import (
    KeggParser, KEGG_NAME_PATTERN, MEASUREMENT_STATUS, DEVICE_STATUS,
)


def _ad(**kw):
    d = dict(timestamp="2026-01-01T00:00:00Z", mac_address="AA:BB:CC:DD:EE:03",
             address_type="public", manufacturer_data=None, service_data=None,
             local_name="kegg")
    d.update(kw)
    return RawAdvertisement(**d)


def _reg():
    r = ParserRegistry()

    @register_parser(name="kegg", local_name_pattern=KEGG_NAME_PATTERN,
                     description="kegg", version="1.0.0", core=False, registry=r)
    class _P(KeggParser):
        pass
    return r


def _scan_record(status4: bytes, cid: bytes = b"\x34\x12", pre: bytes = b"\xaa\xbb") -> bytes:
    """Flags + Complete Local Name 'kegg' + mfr AD — the assumed framing."""
    mfr = cid + pre + status4
    return (bytes([2, 0x01, 0x06]) + bytes([5, 0x09]) + b"kegg"
            + bytes([len(mfr) + 1, 0xFF]) + mfr)


def _mfr_from_record(rec: bytes) -> bytes:
    i = 0
    while i < len(rec):
        ln = rec[i]
        if rec[i + 1] == 0xFF:
            return rec[i + 2:i + 1 + ln]
        i += 1 + ln
    raise AssertionError


class TestMatching:
    def test_exact_name(self):
        assert len(_reg().match(_ad())) == 1

    def test_not_substring(self):
        assert _reg().match(_ad(local_name="keggy")) == []
        assert _reg().match(_ad(local_name="Kegel")) == []


class TestEnums:
    def test_measurement_status(self):
        assert MEASUREMENT_STATUS[2] == "INSERTED"
        assert MEASUREMENT_STATUS[5] == "PROGRAM_SEQUENCE_EXECUTING"
        assert len(MEASUREMENT_STATUS) == 12

    def test_device_status(self):
        assert DEVICE_STATUS[1] == "CHARGING"
        assert DEVICE_STATUS[13] == "OTHER_FAULT"
        assert len(DEVICE_STATUS) == 14


class TestDecode:
    def test_offset_pinned_against_full_scan_record(self):
        rec = _scan_record(bytes([77, 2, 1, 3]))
        assert rec[15:19] == bytes([77, 2, 1, 3])
        r = KeggParser().parse(_ad(manufacturer_data=_mfr_from_record(rec)))
        m = r.metadata
        assert m["battery_percent"] == 77
        assert m["measurement_status"] == "INSERTED"
        assert m["device_status"] == "CHARGING"
        assert m["buffered_measurements"] == 3
        assert m["layout_assumed"] is True

    def test_sensitive_and_identity(self):
        r = KeggParser().parse(_ad())
        assert r.metadata["sensitive"] is True
        assert r.metadata["sensitive_category"] == "reproductive_health"
        assert r.device_class == "medical"
        assert r.identifier_hash == hashlib.sha256(
            b"kegg:AA:BB:CC:DD:EE:03").hexdigest()[:16]
        assert "battery_percent" not in r.metadata

    def test_out_of_range_values_not_decoded(self):
        rec = _scan_record(bytes([200, 2, 1, 0]))
        r = KeggParser().parse(_ad(manufacturer_data=_mfr_from_record(rec)))
        assert "battery_percent" not in r.metadata
        assert r.metadata["mfr_data_hex"] == _mfr_from_record(rec).hex()
        assert r.metadata["mfr_company_id"] == 0x1234

    def test_bad_enum_not_decoded(self):
        rec = _scan_record(bytes([50, 12, 1, 0]))
        r = KeggParser().parse(_ad(manufacturer_data=_mfr_from_record(rec)))
        assert "measurement_status" not in r.metadata

    def test_wrong_name_returns_none(self):
        assert KeggParser().parse(_ad(local_name="other")) is None
