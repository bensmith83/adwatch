"""Tests for Kegtron beer keg monitor plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.kegtron import KegtronParser


COMPANY_ID = b"\xFF\xFF"  # 0xFFFF little-endian


@pytest.fixture
def parser():
    return KegtronParser()


def make_raw(manufacturer_data=None, local_name=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-06T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="public",
        service_data=None,
        service_uuids=[],
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        manufacturer_data=manufacturer_data,
        local_name=local_name,
        **defaults,
    )


def build_kegtron(port=0, keg_size=19000, vol_start=19000, vol_dispensed=5000,
                   port_name="IPA"):
    """Build Kegtron manufacturer data.

    Default: port A, 19L keg, 14L remaining (19000-5000), port named 'IPA'.
    """
    data = COMPANY_ID
    data += bytes([port])
    data += struct.pack("<H", keg_size)
    data += struct.pack("<H", vol_start)
    data += struct.pack("<H", vol_dispensed)
    data += port_name.encode("utf-8") + b"\x00"
    return data


NORMAL_DATA = build_kegtron()


class TestKegtronParsing:
    def test_parse_valid(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="Kegtron")
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="Kegtron")
        result = parser.parse(raw)
        assert result.parser_name == "kegtron"

    def test_beacon_type(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="Kegtron")
        result = parser.parse(raw)
        assert result.beacon_type == "kegtron"

    def test_device_class(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="Kegtron")
        result = parser.parse(raw)
        assert result.device_class == "sensor"

    def test_keg_size(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="Kegtron")
        result = parser.parse(raw)
        assert result.metadata["keg_size_ml"] == 19000

    def test_volume_dispensed(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="Kegtron")
        result = parser.parse(raw)
        assert result.metadata["volume_dispensed_ml"] == 5000

    def test_volume_remaining(self, parser):
        """19000 - 5000 = 14000 mL remaining."""
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="Kegtron")
        result = parser.parse(raw)
        assert result.metadata["volume_remaining_ml"] == 14000

    def test_percent_remaining(self, parser):
        """14000 / 19000 * 100 = ~73.68%."""
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="Kegtron")
        result = parser.parse(raw)
        assert result.metadata["percent_remaining"] == pytest.approx(73.68, abs=0.1)

    def test_port_index(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="Kegtron")
        result = parser.parse(raw)
        assert result.metadata["port"] == 0

    def test_port_name(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="Kegtron")
        result = parser.parse(raw)
        assert result.metadata["port_name"] == "IPA"


class TestKegtronDualTap:
    def test_port_b(self, parser):
        data = build_kegtron(port=1, port_name="Stout")
        raw = make_raw(manufacturer_data=data, local_name="Kegtron")
        result = parser.parse(raw)
        assert result.metadata["port"] == 1
        assert result.metadata["port_name"] == "Stout"


class TestKegtronMatching:
    def test_requires_local_name_kegtron(self, parser):
        """Must have Kegtron-like local name since company ID 0xFFFF is generic."""
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="Kegtron")
        result = parser.parse(raw)
        assert result is not None

    def test_matches_kt_prefix(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="KT-12345")
        result = parser.parse(raw)
        assert result is not None

    def test_rejects_without_kegtron_name(self, parser):
        """0xFFFF without Kegtron name should return None."""
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name=None)
        assert parser.parse(raw) is None

    def test_rejects_wrong_name(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="SomeOtherDevice")
        assert parser.parse(raw) is None


class TestKegtronIdentity:
    def test_identity_hash_format(self, parser):
        raw = make_raw(manufacturer_data=NORMAL_DATA, local_name="Kegtron")
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_identity_hash_uses_mac_and_name(self, parser):
        raw = make_raw(
            manufacturer_data=NORMAL_DATA,
            local_name="Kegtron",
            mac_address="11:22:33:44:55:66",
        )
        result = parser.parse(raw)
        expected = hashlib.sha256("11:22:33:44:55:66:Kegtron".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected


class TestKegtronMalformed:
    def test_returns_none_no_manufacturer_data(self, parser):
        raw = make_raw(manufacturer_data=None, local_name="Kegtron")
        assert parser.parse(raw) is None

    def test_returns_none_too_short(self, parser):
        raw = make_raw(manufacturer_data=COMPANY_ID + bytes(2), local_name="Kegtron")
        assert parser.parse(raw) is None
