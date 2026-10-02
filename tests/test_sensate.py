"""Tests for Sensate relaxation puck plugin.

Per apk-ble-hunting/reports/bioself-sensatepebble_passive.md: discovery is
name-substring only ("Sensate" / "BioSelf" / "ARC BOOT"); no mfr/service data.
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser
from adwatch.plugins.sensate import SensateParser, SENSATE_NAME_PATTERN


def _ad(**kw):
    d = dict(timestamp="2026-01-01T00:00:00Z", mac_address="AA:BB:CC:DD:EE:01",
             address_type="random", manufacturer_data=None, service_data=None)
    d.update(kw)
    return RawAdvertisement(**d)


def _reg():
    r = ParserRegistry()

    @register_parser(name="sensate", local_name_pattern=SENSATE_NAME_PATTERN,
                     description="Sensate", version="1.0.0", core=False, registry=r)
    class _P(SensateParser):
        pass
    return r


class TestMatching:
    def test_matches_sensate_substring(self):
        assert len(_reg().match(_ad(local_name="My Sensate 1234"))) == 1

    def test_matches_bioself(self):
        assert len(_reg().match(_ad(local_name="BioSelf-01"))) == 1

    def test_matches_arc_boot(self):
        assert len(_reg().match(_ad(local_name="ARC BOOT"))) == 1

    def test_matches_factory_variant_case_insensitive(self):
        assert len(_reg().match(_ad(local_name="besensate10"))) == 1

    def test_no_match_other(self):
        assert _reg().match(_ad(local_name="Sense Hat")) == []


class TestParse:
    def test_normal_mode(self):
        r = SensateParser().parse(_ad(local_name="Sensate 1234"))
        assert r.parser_name == "sensate"
        assert r.metadata["vendor"] == "BioSelf"
        assert r.metadata["dfu_mode"] is False
        assert r.metadata["device_name"] == "Sensate 1234"
        assert r.identifier_hash == hashlib.sha256(
            b"sensate:AA:BB:CC:DD:EE:01").hexdigest()[:16]

    def test_dfu_mode(self):
        r = SensateParser().parse(_ad(local_name="ARC BOOT"))
        assert r.metadata["dfu_mode"] is True

    def test_non_matching_returns_none(self):
        assert SensateParser().parse(_ad(local_name="Foo")) is None
        assert SensateParser().parse(_ad()) is None
