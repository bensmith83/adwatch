"""Tests for Omron HealthCare plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.omron import (
    OmronParser, OMRON_COMPANY_ID, OMRON_OXIMETER_UUID, OMRON_SIG_UUIDS,
)


def _make_ad(**kwargs):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "random",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(
        name="omron",
        company_id=OMRON_COMPANY_ID,
        service_uuid=(*OMRON_SIG_UUIDS, OMRON_OXIMETER_UUID),
        local_name_pattern=r"^BLE[sS]mart_",
        description="Omron",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(OmronParser):
        pass
    return _P


def _each_user_data(num_users=1, time_not_set=False, pairing=False, std_mode=False, users=None):
    flags = (num_users - 1) & 0x03
    if time_not_set: flags |= 0x04
    if pairing: flags |= 0x08
    if std_mode: flags |= 0x20
    payload = bytes([0x01, flags])
    users = users or [(100, 5)]  # default: 1 user, seq=100, records=5
    for seq, nrec in users:
        payload += struct.pack("<H", seq) + bytes([nrec])
    cid = struct.pack("<H", OMRON_COMPANY_ID)
    return cid + payload


class TestOmronMatching:
    def test_match_bp_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=["1810"])
        assert len(registry.match(ad)) == 1

    def test_match_company_id(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=_each_user_data())
        assert len(registry.match(ad)) == 1

    def test_match_blesmart_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="BLEsmart_00020001ABCD")
        assert len(registry.match(ad)) == 1


class TestOmronProductClass:
    def test_bp_monitor(self):
        result = OmronParser().parse(_make_ad(service_uuids=["1810"]))
        assert result.metadata["product_class"] == "blood_pressure_monitor"

    def test_glucose_meter(self):
        result = OmronParser().parse(_make_ad(service_uuids=["1808"]))
        assert result.metadata["product_class"] == "glucose_meter"

    def test_weight_scale(self):
        result = OmronParser().parse(_make_ad(service_uuids=["181d"]))
        assert result.metadata["product_class"] == "weight_scale"

    def test_oximeter_uuid(self):
        result = OmronParser().parse(_make_ad(service_uuids=[OMRON_OXIMETER_UUID]))
        assert result.metadata["product_class"] == "pulse_oximeter"


class TestEachUserDataDecode:
    def test_single_user(self):
        result = OmronParser().parse(_make_ad(manufacturer_data=_each_user_data(
            num_users=1, users=[(42, 3)],
        )))
        assert result.metadata["data_type"] == "EachUserData"
        assert result.metadata["number_of_users"] == 1
        assert result.metadata["users"] == [{"last_sequence_number": 42, "number_of_records": 3}]

    def test_four_users(self):
        result = OmronParser().parse(_make_ad(manufacturer_data=_each_user_data(
            num_users=4,
            users=[(10, 1), (20, 2), (30, 3), (40, 4)],
        )))
        assert result.metadata["number_of_users"] == 4
        assert len(result.metadata["users"]) == 4
        assert result.metadata["users"][3]["last_sequence_number"] == 40

    def test_pairing_mode_flag(self):
        result = OmronParser().parse(_make_ad(manufacturer_data=_each_user_data(pairing=True)))
        assert result.metadata["is_pairing_mode"] is True

    def test_time_not_set_flag(self):
        result = OmronParser().parse(_make_ad(manufacturer_data=_each_user_data(time_not_set=True)))
        assert result.metadata["is_time_not_set"] is True

    def test_bluetooth_standard_mode(self):
        result = OmronParser().parse(_make_ad(manufacturer_data=_each_user_data(std_mode=True)))
        assert result.metadata["is_bluetooth_standard_mode"] is True


class TestOmronName:
    def test_name_decoded(self):
        result = OmronParser().parse(_make_ad(local_name="BLEsmart_00020001ABCDEF"))
        assert result.metadata["model_code_hex"] == "0002"
        assert result.metadata["subtype_code_hex"] == "0001"
        assert result.metadata["serial_tail_hex"] == "abcdef"


class TestOmronIdentity:
    def test_identity_uses_serial_tail(self):
        ad = _make_ad(local_name="BLEsmart_00020001DEADBEEF", mac_address="11:22:33:44:55:66")
        result = OmronParser().parse(ad)
        expected = hashlib.sha256(b"omron:0002:deadbeef").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_parse_basics(self):
        result = OmronParser().parse(_make_ad(service_uuids=["1810"]))
        assert result.parser_name == "omron"
        assert result.device_class == "medical"
