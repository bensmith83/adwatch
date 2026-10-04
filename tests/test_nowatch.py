"""Tests for NOWATCH EDA stress wearable plugin.

Per apk-ble-hunting/reports/nowatch-app_passive.md: name `NOWATCH <model+serial>`.
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser
from adwatch.plugins.nowatch import NowatchParser, NOWATCH_NAME_PATTERN


def _ad(**kw):
    d = dict(timestamp="2026-01-01T00:00:00Z", mac_address="E0:11:22:33:44:55",
             address_type="random", manufacturer_data=None, service_data=None)
    d.update(kw)
    return RawAdvertisement(**d)


def _registry():
    reg = ParserRegistry()

    @register_parser(name="nowatch", local_name_pattern=NOWATCH_NAME_PATTERN,
                     description="t", version="1", core=False, registry=reg)
    class _P(NowatchParser):
        pass
    return reg


def test_matches_name():
    assert len(_registry().match(_ad(local_name="NOWATCH MB2900897"))) == 1


def test_no_match_other_name():
    assert _registry().match(_ad(local_name="MyWatch")) == []
    assert _registry().match(_ad(local_name="xNOWATCH")) == []


def test_parse_serial_identity():
    r = NowatchParser().parse(_ad(local_name="NOWATCH MB2900897"))
    assert r.parser_name == "nowatch"
    assert r.device_class == "wearable"
    m = r.metadata
    assert m["unit_id"] == "MB2900897"
    assert m["model_code"] == "MB"
    assert m["serial"] == "2900897"
    assert m["sensitive"] is True
    assert m["sensitive_category"] == "mental_health"
    assert r.identifier_hash == hashlib.sha256(b"nowatch:MB2900897").hexdigest()[:16]


def test_identity_stable_across_mac():
    a = NowatchParser().parse(_ad(local_name="NOWATCH MB2900897"))
    b = NowatchParser().parse(_ad(local_name="NOWATCH MB2900897", mac_address="F1:00:00:00:00:01"))
    assert a.identifier_hash == b.identifier_hash


def test_bare_name_falls_back_to_mac():
    r = NowatchParser().parse(_ad(local_name="NOWATCH"))
    assert "unit_id" not in r.metadata
    assert r.identifier_hash == hashlib.sha256(b"nowatch:E0:11:22:33:44:55").hexdigest()[:16]


def test_unstructured_suffix_kept_as_unit_id():
    m = NowatchParser().parse(_ad(local_name="NOWATCH X-1")).metadata
    assert m["unit_id"] == "X-1"
    assert "model_code" not in m


def test_rejects_other_name():
    assert NowatchParser().parse(_ad(local_name="Watch")) is None
