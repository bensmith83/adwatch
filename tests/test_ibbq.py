"""Tests for iBBQ / Inkbird BBQ thermometer plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

# This import will fail until the plugin is implemented (RED phase)
from adwatch.plugins.ibbq import IBBQParser


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


def _build_ibbq_mfr_data(temps_raw, reserved=b"\x00\x00\x00\x00", mac_bytes=b"\xff\xee\xdd\xcc\xbb\xaa"):
    """Build iBBQ manufacturer data: company_id(2) + reserved(4) + mac(6) + temps(2*N)."""
    data = b"\x00\x00"  # company_id 0x0000 LE
    data += reserved
    data += mac_bytes
    for t in temps_raw:
        data += struct.pack("<h", t)
    return data


class TestIBBQParser:
    def test_two_probe_model(self):
        """IBT-2X: 16 bytes mfr data, parse 2 temps from offset 12."""
        registry = ParserRegistry()

        @register_parser(
            name="ibbq", company_id=0x0000, local_name_pattern=r"^iBBQ$",
            description="iBBQ", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(IBBQParser):
            pass

        # 25.0°C = raw 250, 30.5°C = raw 305
        mfr_data = _build_ibbq_mfr_data([250, 305])
        ad = _make_ad(manufacturer_data=mfr_data, local_name="iBBQ")
        parsers = registry.match(ad)
        assert len(parsers) == 1
        result = parsers[0].parse(ad)
        assert result is not None
        assert result.parser_name == "ibbq"
        assert result.beacon_type == "ibbq"
        assert result.device_class == "sensor"
        assert result.metadata["probe_count"] == 2
        assert result.metadata["probe_1_temp_c"] == 25.0
        assert result.metadata["probe_2_temp_c"] == 30.5

    def test_four_probe_model(self):
        """IBT-4XS: 20 bytes mfr data, parse 4 temps."""
        mfr_data = _build_ibbq_mfr_data([250, 305, 100, 450])
        ad = _make_ad(manufacturer_data=mfr_data, local_name="iBBQ")

        registry = ParserRegistry()

        @register_parser(
            name="ibbq", company_id=0x0000, local_name_pattern=r"^iBBQ$",
            description="iBBQ", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(IBBQParser):
            pass

        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.metadata["probe_count"] == 4
        assert result.metadata["probe_1_temp_c"] == 25.0
        assert result.metadata["probe_2_temp_c"] == 30.5
        assert result.metadata["probe_3_temp_c"] == 10.0
        assert result.metadata["probe_4_temp_c"] == 45.0

    def test_six_probe_model(self):
        """IBT-6XS: 24 bytes mfr data, parse 6 temps."""
        mfr_data = _build_ibbq_mfr_data([250, 305, 100, 450, 200, 550])
        ad = _make_ad(manufacturer_data=mfr_data, local_name="iBBQ")

        registry = ParserRegistry()

        @register_parser(
            name="ibbq", company_id=0x0000, local_name_pattern=r"^iBBQ$",
            description="iBBQ", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(IBBQParser):
            pass

        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.metadata["probe_count"] == 6
        assert result.metadata["probe_5_temp_c"] == 20.0
        assert result.metadata["probe_6_temp_c"] == 55.0

    def test_disconnected_probe_sentinel(self):
        """Disconnected probe sentinel 0xFFF6 (-10 signed) should be skipped."""
        # 0xFFF6 as signed int16 = -10
        mfr_data = _build_ibbq_mfr_data([250, -10])
        ad = _make_ad(manufacturer_data=mfr_data, local_name="iBBQ")

        registry = ParserRegistry()

        @register_parser(
            name="ibbq", company_id=0x0000, local_name_pattern=r"^iBBQ$",
            description="iBBQ", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(IBBQParser):
            pass

        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.metadata["probe_1_temp_c"] == 25.0
        assert "probe_2_temp_c" not in result.metadata

    def test_negative_temperature(self):
        """Negative temperatures should be handled (int16 signed)."""
        # -5.0°C = raw -50
        mfr_data = _build_ibbq_mfr_data([-50, 100])
        ad = _make_ad(manufacturer_data=mfr_data, local_name="iBBQ")

        registry = ParserRegistry()

        @register_parser(
            name="ibbq", company_id=0x0000, local_name_pattern=r"^iBBQ$",
            description="iBBQ", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(IBBQParser):
            pass

        result = registry.match(ad)[0].parse(ad)
        assert result is not None
        assert result.metadata["probe_1_temp_c"] == -5.0
        assert result.metadata["probe_2_temp_c"] == 10.0

    def test_probe_count_from_data_length(self):
        """Probe count = (len - 12) / 2."""
        # 2 probes = 16 bytes total
        mfr_data = _build_ibbq_mfr_data([100, 200])
        assert len(mfr_data) == 16

        # 4 probes = 20 bytes total
        mfr_data = _build_ibbq_mfr_data([100, 200, 300, 400])
        assert len(mfr_data) == 20

        # 6 probes = 24 bytes total
        mfr_data = _build_ibbq_mfr_data([100, 200, 300, 400, 500, 600])
        assert len(mfr_data) == 24

    def test_match_by_local_name(self):
        """Should match by local_name 'iBBQ' (exact)."""
        registry = ParserRegistry()

        @register_parser(
            name="ibbq", company_id=0x0000, local_name_pattern=r"^iBBQ$",
            description="iBBQ", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(IBBQParser):
            pass

        ad = _make_ad(local_name="iBBQ", manufacturer_data=_build_ibbq_mfr_data([100, 200]))
        assert len(registry.match(ad)) == 1

    def test_no_match_wrong_name(self):
        """Should not match with wrong local name and no mfr data."""
        registry = ParserRegistry()

        @register_parser(
            name="ibbq", local_name_pattern=r"^iBBQ$",
            description="iBBQ", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(IBBQParser):
            pass

        ad = _make_ad(local_name="SomeOtherDevice")
        assert len(registry.match(ad)) == 0

    def test_identity_hash(self):
        """Identity hash: SHA256('{mac}:iBBQ')[:16]."""
        mfr_data = _build_ibbq_mfr_data([250, 305])
        ad = _make_ad(
            manufacturer_data=mfr_data,
            local_name="iBBQ",
            mac_address="11:22:33:44:55:66",
        )

        registry = ParserRegistry()

        @register_parser(
            name="ibbq", company_id=0x0000, local_name_pattern=r"^iBBQ$",
            description="iBBQ", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(IBBQParser):
            pass

        result = registry.match(ad)[0].parse(ad)
        expected = hashlib.sha256("11:22:33:44:55:66:iBBQ".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_too_short_data_returns_none(self):
        """Manufacturer data shorter than 14 bytes should return None."""
        mfr_data = b"\x00\x00\x00\x00\x00\x00"  # Only 6 bytes
        ad = _make_ad(manufacturer_data=mfr_data, local_name="iBBQ")

        registry = ParserRegistry()

        @register_parser(
            name="ibbq", company_id=0x0000, local_name_pattern=r"^iBBQ$",
            description="iBBQ", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(IBBQParser):
            pass

        result = registry.match(ad)[0].parse(ad)
        assert result is None
