"""Tests for Hyperice recovery-device plugin (Hypervolt / Normatec / Venom / X).

Per apk-ble-hunting/reports/hyperice-app_passive.md. The app reads mfr data
via ScanRecord.getManufacturerSpecificData() -> SparseArray.get(2234), which
already strips the 2-byte company ID, so the report's offsets [0] (model)
and [7] (submodel) are relative to ``manufacturer_payload`` (no -2 shift).
"""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.hyperice import (
    HypericeParser,
    HYPERICE_COMPANY_ID,
    NORDIC_COMPANY_ID,
    MODEL_NUMBERS,
    SUBMODELS,
    DFU_NAMES,
    DFU_NAME_PATTERN,
)


def _make_ad(**kwargs):
    defaults = {
        "timestamp": "2026-10-01T00:00:00Z",
        "mac_address": "D1:22:33:44:55:66",
        "address_type": "random",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _mfr(payload: bytes, cid: int = HYPERICE_COMPANY_ID) -> bytes:
    return struct.pack("<H", cid) + payload


def _register(registry):
    @register_parser(
        name="hyperice",
        company_id=HYPERICE_COMPANY_ID,
        local_name_pattern=DFU_NAME_PATTERN,
        description="Hyperice",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(HypericeParser):
        pass

    return _P


class TestConstants:
    def test_company_ids(self):
        assert HYPERICE_COMPANY_ID == 0x08BA == 2234
        assert NORDIC_COMPANY_ID == 0x0059

    def test_model_table(self):
        assert MODEL_NUMBERS[1] == "Hypervolt"
        assert MODEL_NUMBERS[9] == "Normatec 3"
        assert MODEL_NUMBERS[13] == "Venom 2"
        assert MODEL_NUMBERS[35] == "Hyperice X 2 (secondary)"
        assert len(MODEL_NUMBERS) == 28

    def test_submodels(self):
        assert SUBMODELS == {0: "RYDER", 1: "MINEW"}

    def test_dfu_names(self):
        assert len(DFU_NAMES) == 25
        assert "NT3_DFU_TARGET" in DFU_NAMES
        assert "HX2 DfuTarg" in DFU_NAMES


class TestMatching:
    def test_cid_match(self):
        reg = ParserRegistry()
        _register(reg)
        assert len(reg.match(_make_ad(manufacturer_data=_mfr(b"\x05")))) == 1

    @pytest.mark.parametrize("name", ["HypervoltDFU", "NT3_DFU_TARGET", "Hyperice X DFU",
                                      "HX2 DfuTarg", "Vyper 3.0 DFU"])
    def test_dfu_name_match(self, name):
        reg = ParserRegistry()
        _register(reg)
        ad = _make_ad(local_name=name, manufacturer_data=_mfr(b"\x00", NORDIC_COMPANY_ID))
        assert len(reg.match(ad)) == 1

    def test_nordic_cid_alone_not_matched(self):
        reg = ParserRegistry()
        _register(reg)
        ad = _make_ad(local_name="Thingy", manufacturer_data=_mfr(b"\x00", NORDIC_COMPANY_ID))
        assert reg.match(ad) == []

    def test_generic_dfutarg_not_matched(self):
        """Bare 'DfuTarg' is Nordic's SDK default — not Hyperice-specific."""
        reg = ParserRegistry()
        _register(reg)
        ad = _make_ad(local_name="DfuTarg", manufacturer_data=_mfr(b"\x00", NORDIC_COMPANY_ID))
        assert reg.match(ad) == []

    def test_dfu_name_is_exact(self):
        reg = ParserRegistry()
        _register(reg)
        assert reg.match(_make_ad(local_name="HypervoltDFUx")) == []
        assert reg.match(_make_ad(local_name="xNT LL DFU")) == []


class TestParse:
    def test_model_decode(self):
        payload = bytes([5]) + bytes(7)
        r = HypericeParser().parse(_make_ad(manufacturer_data=_mfr(payload)))
        assert r.parser_name == "hyperice"
        assert r.device_class == "recovery"
        assert r.metadata["model_number"] == 5
        assert r.metadata["model"] == "Hypervolt 2"
        assert r.metadata["dfu_mode"] is False
        assert "submodel" not in r.metadata

    @pytest.mark.parametrize("model", [9, 20])
    def test_normatec3_submodel(self, model):
        payload = bytes([model, 0, 0, 0, 0, 0, 0, 1])
        m = HypericeParser().parse(_make_ad(manufacturer_data=_mfr(payload))).metadata
        assert m["submodel_code"] == 1
        assert m["submodel"] == "MINEW"

    def test_submodel_only_for_normatec3(self):
        payload = bytes([5, 0, 0, 0, 0, 0, 0, 1])
        m = HypericeParser().parse(_make_ad(manufacturer_data=_mfr(payload))).metadata
        assert "submodel" not in m

    def test_normatec3_short_payload_no_submodel(self):
        m = HypericeParser().parse(_make_ad(manufacturer_data=_mfr(bytes([9, 0])))).metadata
        assert m["model"] == "Normatec 3"
        assert "submodel" not in m

    def test_unknown_model(self):
        m = HypericeParser().parse(_make_ad(manufacturer_data=_mfr(bytes([99])))).metadata
        assert m["model"] == "unknown_99"

    def test_hypervolt_plus_name_disambiguation(self):
        ad = _make_ad(manufacturer_data=_mfr(bytes([1])), local_name="Hypervolt+ 1234")
        assert HypericeParser().parse(ad).metadata["model"] == "Hypervolt Plus"
        ad = _make_ad(manufacturer_data=_mfr(bytes([1])), local_name="Hypervolt Plus")
        assert HypericeParser().parse(ad).metadata["model"] == "Hypervolt Plus"

    def test_premier_hip_name_disambiguation(self):
        ad = _make_ad(manufacturer_data=_mfr(bytes([25])), local_name="Normatec Premier Hip")
        assert HypericeParser().parse(ad).metadata["model"] == "Normatec Premier Hip"

    def test_identity_mac_and_model(self):
        ad = _make_ad(manufacturer_data=_mfr(bytes([5])))
        r = HypericeParser().parse(ad)
        expected = hashlib.sha256(b"hyperice:D1:22:33:44:55:66:5").hexdigest()[:16]
        assert r.identifier_hash == expected

    def test_dfu_mode_nordic(self):
        ad = _make_ad(local_name="NT3_DFU_TARGET", manufacturer_data=_mfr(b"\x01\x02", NORDIC_COMPANY_ID))
        r = HypericeParser().parse(ad)
        assert r is not None
        assert r.metadata["dfu_mode"] is True
        assert r.metadata["dfu_name"] == "NT3_DFU_TARGET"
        assert r.metadata["dfu_family"] == "Normatec"
        assert "model_number" not in r.metadata

    def test_dfu_name_without_mfr(self):
        r = HypericeParser().parse(_make_ad(local_name="Venom2DfuTarg"))
        assert r.metadata["dfu_family"] == "Venom"

    def test_nordic_without_dfu_name_rejected(self):
        ad = _make_ad(local_name="SomeNordicThing", manufacturer_data=_mfr(b"\x01", NORDIC_COMPANY_ID))
        assert HypericeParser().parse(ad) is None

    def test_generic_dfutarg_rejected(self):
        ad = _make_ad(local_name="DfuTarg", manufacturer_data=_mfr(b"\x01", NORDIC_COMPANY_ID))
        assert HypericeParser().parse(ad) is None

    def test_unrelated_rejected(self):
        assert HypericeParser().parse(_make_ad(manufacturer_data=_mfr(b"\x01", 0x004C))) is None

    def test_empty_hyperice_payload_presence(self):
        r = HypericeParser().parse(_make_ad(manufacturer_data=struct.pack("<H", HYPERICE_COMPANY_ID)))
        assert r is not None
        assert "model_number" not in r.metadata
