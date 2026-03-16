"""Tests for Xiaogui Scale plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser


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


def _build_mfr_data(flags, impedance=0, weight_raw=0, extra=b""):
    """Build manufacturer_data: flags(1) + impedance(2 LE) + weight(2 LE) + extra."""
    return struct.pack("<BHH", flags, impedance, weight_raw) + extra


class TestXiaoguiScaleParser:
    def _registry_and_parser(self):
        from adwatch.plugins.xiaogui_scale import XiaoguiScaleParser

        registry = ParserRegistry()

        @register_parser(
            name="xiaogui_scale",
            local_name_pattern=r"^(Xiaogui|TZC)",
            description="Xiaogui smart scale",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class TestParser(XiaoguiScaleParser):
            pass

        return registry

    def test_match_by_local_name_xiaogui(self):
        """Should match advertisements with local_name starting with 'Xiaogui'."""
        registry = self._registry_and_parser()
        mfr_data = _build_mfr_data(0x00)
        ad = _make_ad(manufacturer_data=mfr_data, local_name="Xiaogui Scale")
        assert len(registry.match(ad)) == 1

    def test_match_by_local_name_tzc(self):
        """Should match advertisements with local_name starting with 'TZC'."""
        registry = self._registry_and_parser()
        mfr_data = _build_mfr_data(0x00)
        ad = _make_ad(manufacturer_data=mfr_data, local_name="TZC4-B")
        assert len(registry.match(ad)) == 1

    def test_no_match_wrong_name(self):
        """Should not match with unrelated local_name."""
        registry = self._registry_and_parser()
        mfr_data = _build_mfr_data(0x00)
        ad = _make_ad(manufacturer_data=mfr_data, local_name="SomeOtherScale")
        assert len(registry.match(ad)) == 0

    def test_weight_kg_stabilized(self):
        """Stabilized weight in kg."""
        registry = self._registry_and_parser()
        # flags: bit 0 = stabilized => 0x01
        # weight_raw = 755 => 75.5 kg
        mfr_data = _build_mfr_data(flags=0x01, impedance=0, weight_raw=755)
        ad = _make_ad(manufacturer_data=mfr_data, local_name="Xiaogui")
        result = registry.match(ad)[0].parse(ad)

        assert result is not None
        assert result.parser_name == "xiaogui_scale"
        assert result.beacon_type == "xiaogui_scale"
        assert result.device_class == "sensor"
        assert result.metadata["weight"] == pytest.approx(75.5)
        assert result.metadata["unit"] == "kg"
        assert result.metadata["stabilized"] is True
        assert result.metadata["weight_removed"] is False
        assert result.metadata["impedance"] is None

    def test_weight_lbs(self):
        """Weight in lbs (unit flag bit 4 set)."""
        registry = self._registry_and_parser()
        # flags: bit 4 = lbs => 0x10
        # weight_raw = 1654 => 165.4 lbs
        mfr_data = _build_mfr_data(flags=0x10, impedance=0, weight_raw=1654)
        ad = _make_ad(manufacturer_data=mfr_data, local_name="Xiaogui")
        result = registry.match(ad)[0].parse(ad)

        assert result is not None
        assert result.metadata["weight"] == pytest.approx(165.4)
        assert result.metadata["unit"] == "lbs"
        assert result.metadata["stabilized"] is False

    def test_weight_removed_flag(self):
        """Weight removed flag (bit 1)."""
        registry = self._registry_and_parser()
        # flags: bit 1 = weight_removed => 0x02
        mfr_data = _build_mfr_data(flags=0x02, impedance=0, weight_raw=500)
        ad = _make_ad(manufacturer_data=mfr_data, local_name="Xiaogui")
        result = registry.match(ad)[0].parse(ad)

        assert result is not None
        assert result.metadata["weight_removed"] is True
        assert result.metadata["stabilized"] is False

    def test_impedance_present(self):
        """Impedance data when flags bit 5 is set."""
        registry = self._registry_and_parser()
        # flags: bit 5 = impedance present, bit 0 = stabilized => 0x21
        # impedance = 512 ohms, weight = 680 => 68.0 kg
        mfr_data = _build_mfr_data(flags=0x21, impedance=512, weight_raw=680)
        ad = _make_ad(manufacturer_data=mfr_data, local_name="Xiaogui")
        result = registry.match(ad)[0].parse(ad)

        assert result is not None
        assert result.metadata["impedance"] == 512
        assert result.metadata["weight"] == pytest.approx(68.0)
        assert result.metadata["stabilized"] is True

    def test_impedance_absent_when_flag_not_set(self):
        """Impedance is None when flags bit 5 is not set, even if bytes are nonzero."""
        registry = self._registry_and_parser()
        # flags=0x00, impedance bytes=9999 but flag not set
        mfr_data = _build_mfr_data(flags=0x00, impedance=9999, weight_raw=500)
        ad = _make_ad(manufacturer_data=mfr_data, local_name="Xiaogui")
        result = registry.match(ad)[0].parse(ad)

        assert result is not None
        assert result.metadata["impedance"] is None

    def test_all_flags_set(self):
        """All relevant flags set: stabilized + weight_removed + lbs + impedance."""
        registry = self._registry_and_parser()
        # flags: 0x01 | 0x02 | 0x10 | 0x20 = 0x33
        mfr_data = _build_mfr_data(flags=0x33, impedance=480, weight_raw=1500)
        ad = _make_ad(manufacturer_data=mfr_data, local_name="TZC4")
        result = registry.match(ad)[0].parse(ad)

        assert result is not None
        assert result.metadata["stabilized"] is True
        assert result.metadata["weight_removed"] is True
        assert result.metadata["unit"] == "lbs"
        assert result.metadata["weight"] == pytest.approx(150.0)
        assert result.metadata["impedance"] == 480

    def test_no_manufacturer_data(self):
        """No manufacturer data returns None."""
        from adwatch.plugins.xiaogui_scale import XiaoguiScaleParser

        parser = XiaoguiScaleParser()
        ad = _make_ad(manufacturer_data=None, local_name="Xiaogui")
        result = parser.parse(ad)
        assert result is None

    def test_manufacturer_data_too_short(self):
        """Manufacturer data shorter than 5 bytes returns None."""
        from adwatch.plugins.xiaogui_scale import XiaoguiScaleParser

        parser = XiaoguiScaleParser()
        ad = _make_ad(manufacturer_data=b"\x01\x02\x03", local_name="Xiaogui")
        result = parser.parse(ad)
        assert result is None

    def test_identity_hash(self):
        """Identity hash: SHA256('{mac}:xiaogui_scale')[:16]."""
        registry = self._registry_and_parser()
        mfr_data = _build_mfr_data(flags=0x01, weight_raw=700)
        ad = _make_ad(
            manufacturer_data=mfr_data,
            local_name="Xiaogui",
            mac_address="11:22:33:44:55:66",
        )
        result = registry.match(ad)[0].parse(ad)

        expected = hashlib.sha256("11:22:33:44:55:66:xiaogui_scale".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_zero_weight(self):
        """Zero weight is valid (empty scale)."""
        registry = self._registry_and_parser()
        mfr_data = _build_mfr_data(flags=0x00, weight_raw=0)
        ad = _make_ad(manufacturer_data=mfr_data, local_name="Xiaogui")
        result = registry.match(ad)[0].parse(ad)

        assert result is not None
        assert result.metadata["weight"] == pytest.approx(0.0)

    def test_raw_payload_hex(self):
        """raw_payload_hex contains full manufacturer_data hex."""
        registry = self._registry_and_parser()
        mfr_data = _build_mfr_data(flags=0x01, impedance=100, weight_raw=750)
        ad = _make_ad(manufacturer_data=mfr_data, local_name="Xiaogui")
        result = registry.match(ad)[0].parse(ad)

        assert result.raw_payload_hex == mfr_data.hex()
