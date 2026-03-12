"""Tests for Xiaomi Mi Scale plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.mi_scale import MiScaleParser


@pytest.fixture
def parser():
    return MiScaleParser()


def make_raw(service_data=None, local_name=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-06T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="public",
        manufacturer_data=None,
        service_uuids=[],
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        service_data=service_data,
        local_name=local_name,
        **defaults,
    )


def build_v1_data(weight_raw=15000, flags=0x0030, year=2026, month=3, day=6,
                   hour=12, minute=30, second=0):
    """Build 10-byte Mi Scale v1 service data (UUID 181d).

    Default: 75.0 kg (15000/200), stabilized+removed.
    flags bit 4=stabilized, bit 5=removed → 0x0030
    """
    data = struct.pack("<H", flags)
    data += struct.pack("<H", year)
    data += bytes([month, day, hour, minute, second])
    data += struct.pack("<H", weight_raw)
    return data


def build_v2_data(weight_raw=15000, impedance=500, flags=0x0030, year=2026,
                   month=3, day=6, hour=12, minute=30, second=0):
    """Build 13-byte Mi Scale v2 service data (UUID 181b)."""
    data = build_v1_data(weight_raw=weight_raw, flags=flags, year=year,
                          month=month, day=day, hour=hour, minute=minute,
                          second=second)
    data += struct.pack("<H", impedance)
    return data


V1_DATA = build_v1_data()
V2_DATA = build_v2_data()


class TestMiScaleV1:
    def test_parse_valid(self, parser):
        raw = make_raw(service_data={"181d": V1_DATA})
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(service_data={"181d": V1_DATA})
        result = parser.parse(raw)
        assert result.parser_name == "mi_scale"

    def test_beacon_type(self, parser):
        raw = make_raw(service_data={"181d": V1_DATA})
        result = parser.parse(raw)
        assert result.beacon_type == "mi_scale"

    def test_device_class(self, parser):
        raw = make_raw(service_data={"181d": V1_DATA})
        result = parser.parse(raw)
        assert result.device_class == "sensor"

    def test_weight_kg(self, parser):
        """15000 / 200 = 75.0 kg."""
        raw = make_raw(service_data={"181d": V1_DATA})
        result = parser.parse(raw)
        assert result.metadata["weight_kg"] == pytest.approx(75.0)

    def test_stabilized_flag(self, parser):
        raw = make_raw(service_data={"181d": V1_DATA})
        result = parser.parse(raw)
        assert result.metadata["stabilized"] is True

    def test_weight_removed_flag(self, parser):
        raw = make_raw(service_data={"181d": V1_DATA})
        result = parser.parse(raw)
        assert result.metadata["weight_removed"] is True

    def test_unit_kg(self, parser):
        """flags bit 0 = 0 → kg."""
        raw = make_raw(service_data={"181d": V1_DATA})
        result = parser.parse(raw)
        assert result.metadata["unit"] == "kg"


class TestMiScaleV1Lbs:
    def test_weight_lbs(self, parser):
        """flags bit 0 = 1 → lbs, divide by 100."""
        data = build_v1_data(weight_raw=16535, flags=0x0031)  # bit 0 set
        raw = make_raw(service_data={"181d": data})
        result = parser.parse(raw)
        assert result.metadata["unit"] == "lbs"
        assert result.metadata["weight_lbs"] == pytest.approx(165.35)


class TestMiScaleV2:
    def test_parse_valid(self, parser):
        raw = make_raw(service_data={"181b": V2_DATA})
        result = parser.parse(raw)
        assert result is not None

    def test_impedance(self, parser):
        raw = make_raw(service_data={"181b": V2_DATA})
        result = parser.parse(raw)
        assert result.metadata["impedance"] == 500

    def test_weight_kg_v2(self, parser):
        raw = make_raw(service_data={"181b": V2_DATA})
        result = parser.parse(raw)
        assert result.metadata["weight_kg"] == pytest.approx(75.0)

    def test_version_v2(self, parser):
        raw = make_raw(service_data={"181b": V2_DATA})
        result = parser.parse(raw)
        assert result.metadata["version"] == 2


class TestMiScaleIdentity:
    def test_identity_hash_format(self, parser):
        raw = make_raw(service_data={"181d": V1_DATA})
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_identity_hash_uses_mac(self, parser):
        raw = make_raw(
            service_data={"181d": V1_DATA},
            mac_address="11:22:33:44:55:66",
            local_name="MIBFS",
        )
        result = parser.parse(raw)
        expected = hashlib.sha256("11:22:33:44:55:66:MIBFS".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected


class TestMiScaleMalformed:
    def test_returns_none_no_service_data(self, parser):
        raw = make_raw(service_data=None)
        assert parser.parse(raw) is None

    def test_returns_none_wrong_uuid(self, parser):
        raw = make_raw(service_data={"abcd": V1_DATA})
        assert parser.parse(raw) is None

    def test_returns_none_too_short(self, parser):
        raw = make_raw(service_data={"181d": bytes(5)})
        assert parser.parse(raw) is None
