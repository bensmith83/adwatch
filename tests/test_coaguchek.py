"""Tests for Roche CoaguChek INRange / Vantus INR meter plugin.

Per apk-ble-hunting/reports/biotelemetry-remoteinr_passive.md: discovery is
MAC OUI B8:78:79 only; nothing decodable is advertised.
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser
from adwatch.plugins.coaguchek import CoaguChekParser, COAGUCHEK_OUI


def _ad(**kw):
    d = dict(timestamp="2026-01-01T00:00:00Z", mac_address="B8:78:79:12:34:56",
             address_type="public", manufacturer_data=None, service_data=None)
    d.update(kw)
    return RawAdvertisement(**d)


def _registry():
    reg = ParserRegistry()

    @register_parser(name="coaguchek", mac_prefix=COAGUCHEK_OUI,
                     description="t", version="1", core=False, registry=reg)
    class _P(CoaguChekParser):
        pass
    return reg


def test_oui_constant():
    assert COAGUCHEK_OUI == "B8:78:79"


def test_matches_oui():
    assert len(_registry().match(_ad(local_name="Meter"))) == 1


def test_matches_oui_lowercase_mac():
    assert len(_registry().match(_ad(mac_address="b8:78:79:aa:bb:cc"))) == 1


def test_no_match_other_mac():
    assert _registry().match(_ad(mac_address="B8:78:7A:12:34:56")) == []


def test_parse_identity_and_metadata():
    r = CoaguChekParser().parse(_ad(local_name="SomeMeter"))
    assert r.parser_name == "coaguchek"
    assert r.device_class == "medical"
    assert r.identifier_hash == hashlib.sha256(b"coaguchek:B8:78:79:12:34:56").hexdigest()[:16]
    assert r.metadata["sensitive"] is True
    assert r.metadata["sensitive_category"] == "anticoagulation_therapy"
    assert r.metadata["device_name"] == "SomeMeter"
    assert r.metadata["name_present"] is True


def test_parse_without_name():
    r = CoaguChekParser().parse(_ad())
    assert r is not None
    assert r.metadata["name_present"] is False


def test_parse_rejects_non_oui():
    assert CoaguChekParser().parse(_ad(mac_address="11:22:33:44:55:66")) is None
