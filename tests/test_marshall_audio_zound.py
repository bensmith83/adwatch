"""Tests for Zound Industries (Marshall / adidas / Urbanears) mfr-data enrichment.

Source: apk-ble-hunting reports/zoundindustries-marshallbt_{passive,native}.md.
Payload offsets are post-CID (== RawAdvertisement.manufacturer_payload).
"""

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser
from adwatch.plugins.marshall_audio import (
    MarshallAudioParser,
    MARSHALL_SERVICE_UUID,
    ZOUND_COMPANY_IDS,
    ZOUND_NAME_PATTERN,
)


def _ad(**kw):
    d = dict(timestamp="2026-10-01T00:00:00Z", mac_address="AA:BB:CC:DD:EE:FF",
             address_type="random", manufacturer_data=None, service_data=None)
    d.update(kw)
    return RawAdvertisement(**d)


def _payload(model=14, color=2, pairing=0x01):
    return bytes([model, color, 0, 0, 0, 0, 0, 0, pairing, 0])


@pytest.fixture
def parser():
    return MarshallAudioParser()


def _registry():
    reg = ParserRegistry()

    @register_parser(name="marshall_audio", service_uuid=MARSHALL_SERVICE_UUID,
                     company_id=ZOUND_COMPANY_IDS, local_name_pattern=ZOUND_NAME_PATTERN,
                     description="x", version="1", core=False, registry=reg)
    class P(MarshallAudioParser):
        pass

    return reg


class TestZoundRegistration:
    def test_company_ids_both_byte_orders(self):
        assert set(ZOUND_COMPANY_IDS) == {0x065A, 0x5A06}

    @pytest.mark.parametrize("cid_bytes", [b"\x5a\x06", b"\x06\x5a"])
    def test_registry_matches_either_order(self, cid_bytes):
        assert len(_registry().match(_ad(manufacturer_data=cid_bytes + _payload()))) == 1

    @pytest.mark.parametrize("name", ["LE-MINOR III", "LE-adidas Z.N.E. 01"])
    def test_registry_matches_le_names(self, name):
        assert len(_registry().match(_ad(local_name=name))) == 1

    def test_live_registry_has_zound_cids(self):
        from adwatch.registry import _default_registry
        import adwatch.plugins.marshall_audio  # noqa: F401
        ad = _ad(manufacturer_data=b"\x5a\x06" + _payload())
        names = [type(p).__name__ for p in _default_registry.match(ad)]
        assert "MarshallAudioParser" in names


class TestZoundDecode:
    @pytest.mark.parametrize("cid_bytes", [b"\x5a\x06", b"\x06\x5a"])
    def test_decodes_model_color_pairing(self, parser, cid_bytes):
        r = parser.parse(_ad(manufacturer_data=cid_bytes + _payload(model=14, color=2, pairing=1)))
        assert r is not None
        assert r.parser_name == "marshall_audio"
        assert r.metadata["model_type"] == 14
        assert r.metadata["model_codename"] == "EMBERTON_II"
        assert r.metadata["color_id"] == 2
        assert r.metadata["pairing_mode"] is True

    def test_not_pairing(self, parser):
        r = parser.parse(_ad(manufacturer_data=b"\x5a\x06" + _payload(pairing=0)))
        assert r.metadata["pairing_mode"] is False

    def test_short_payload_no_pairing_field(self, parser):
        r = parser.parse(_ad(manufacturer_data=b"\x5a\x06" + bytes([15, 1])))
        assert r.metadata["model_codename"] == "JETT"
        assert "pairing_mode" not in r.metadata

    def test_unknown_model(self, parser):
        r = parser.parse(_ad(manufacturer_data=b"\x5a\x06" + _payload(model=200)))
        assert r.metadata["model_codename"] == "Unknown"

    @pytest.mark.parametrize("model,code", [(0, "ARNOLD"), (17, "ASLLANI"), (41, "LYKKE"),
                                            (98, "ASLLANI_RAW"), (99, "JETT_RAW")])
    def test_model_table(self, parser, model, code):
        r = parser.parse(_ad(manufacturer_data=b"\x5a\x06" + _payload(model=model)))
        assert r.metadata["model_codename"] == code

    def test_cid_only_no_payload_returns_none(self, parser):
        assert parser.parse(_ad(manufacturer_data=b"\x5a\x06")) is None

    def test_name_only_le_minor(self, parser):
        r = parser.parse(_ad(local_name="LE-MINOR III"))
        assert r is not None
        assert r.metadata["model"] == "Minor III"
        assert r.metadata["device_name"] == "LE-MINOR III"

    def test_name_only_adidas(self, parser):
        r = parser.parse(_ad(local_name="LE-adidas Z.N.E. 01"))
        assert r.metadata["model"] == "adidas Z.N.E. 01"

    def test_unrelated_cid_with_name_unknown_still_none(self, parser):
        assert parser.parse(_ad(manufacturer_data=b"\x34\x12\x01\x02", local_name="Foo")) is None

    def test_identity_mac_based(self, parser):
        import hashlib
        r = parser.parse(_ad(manufacturer_data=b"\x5a\x06" + _payload(), mac_address="11:22:33:44:55:66"))
        assert r.identifier_hash == hashlib.sha256(b"11:22:33:44:55:66:marshall_audio").hexdigest()[:16]
