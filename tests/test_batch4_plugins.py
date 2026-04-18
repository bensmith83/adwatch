"""Tests for batch 4 outdoor/tool/irrigation plugins."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement


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


def _mfr(company_id: int, payload: bytes = b"") -> bytes:
    return struct.pack("<H", company_id) + payload


# ---- Mammotion -------------------------------------------------------------

class TestMammotion:
    @pytest.fixture
    def parser(self):
        from adwatch.plugins.mammotion import MammotionParser
        return MammotionParser()

    def test_matches_company_id(self, parser):
        ad = _make_ad(manufacturer_data=_mfr(0x01A8, bytes(12)))
        assert parser.parse(ad) is not None

    def test_matches_luba_name(self, parser):
        ad = _make_ad(local_name="Luba-001234")
        assert parser.parse(ad) is not None

    def test_product_id_ascii_decode(self, parser):
        # "HM430" reversed = "034MH" → reversed back by parser to ASCII
        pid_bytes = b"HM43"[::-1]  # reversed in payload
        payload = bytes([0x08, 0x00]) + pid_bytes + bytes(6)
        ad = _make_ad(manufacturer_data=_mfr(0x01A8, payload))
        result = parser.parse(ad)
        assert result.metadata["product_id"] == "HM43"

    def test_device_class(self, parser):
        ad = _make_ad(manufacturer_data=_mfr(0x01A8, bytes(12)))
        assert parser.parse(ad).device_class == "mower"


# ---- Husqvarna -------------------------------------------------------------

class TestHusqvarna:
    @pytest.fixture
    def parser(self):
        from adwatch.plugins.husqvarna import HusqvarnaParser
        return HusqvarnaParser()

    def _tlv(self, t: int, value: bytes) -> bytes:
        return bytes([1 + len(value), t]) + value

    def test_parses_serial_and_state(self, parser):
        serial_tlv = self._tlv(0x04, struct.pack("<I", 123456789))
        mower_status_tlv = self._tlv(0x05, bytes([0, 6, 3]))  # not-pairable, InOperation, Mowing
        product_type_tlv = self._tlv(0x06, bytes([10, 1, 2]))  # Mower group
        payload = serial_tlv + mower_status_tlv + product_type_tlv
        ad = _make_ad(manufacturer_data=_mfr(0x0426, payload))
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["serial_number"] == 123456789
        assert result.metadata["state"] == "InOperation"
        assert result.metadata["activity"] == "Mowing"
        assert result.metadata["device_group"] == "Mower"

    def test_service_uuid_only(self, parser):
        from adwatch.plugins.husqvarna import HUSQVARNA_SERVICE_UUID
        ad = _make_ad(service_uuids=[HUSQVARNA_SERVICE_UUID])
        assert parser.parse(ad) is not None

    def test_identity_from_serial(self, parser):
        payload = self._tlv(0x04, struct.pack("<I", 42))
        ad = _make_ad(manufacturer_data=_mfr(0x0426, payload))
        result = parser.parse(ad)
        expected = hashlib.sha256("husqvarna:42".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_device_class_mower(self, parser):
        ad = _make_ad(manufacturer_data=_mfr(0x0426, b""))
        assert parser.parse(ad).device_class == "mower"


# ---- Worx Landroid ---------------------------------------------------------

class TestWorxLandroid:
    @pytest.fixture
    def parser(self):
        from adwatch.plugins.worx_landroid import WorxLandroidParser
        return WorxLandroidParser()

    def test_service_uuid_match(self, parser):
        ad = _make_ad(service_uuids=["abf0"])
        result = parser.parse(ad)
        assert result is not None
        assert result.device_class == "mower"

    def test_no_match(self, parser):
        assert parser.parse(_make_ad()) is None


# ---- Segway Navimow --------------------------------------------------------

class TestSegwayNavimow:
    @pytest.fixture
    def parser(self):
        from adwatch.plugins.segway_navimow import SegwayNavimowParser
        return SegwayNavimowParser()

    def _navimow_mfr(self, body: bytes) -> bytes:
        # body = [ble_type, proto_version, ...body_bytes]; checksum appended.
        checksum = (~sum(body)) & 0xFF
        return struct.pack("<H", 0x4E42) + body + bytes([checksum])

    def test_matches_mower_type(self, parser):
        body = bytes([0xE0, 2, 0x01, 0x02, 0x03])
        ad = _make_ad(manufacturer_data=self._navimow_mfr(body))
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["ble_type_code"] == 0xE0
        assert result.metadata["protocol_version"] == 2
        assert result.metadata["checksum_valid"] is True

    def test_findmy_variant_extracts_serial(self, parser):
        # Offset 5 in payload = 1 → FindMy; bytes 6+ = ASCII SN.
        body = bytes([0xE0, 2, 0, 0, 0, 1]) + b"SN123456"
        ad = _make_ad(manufacturer_data=self._navimow_mfr(body))
        result = parser.parse(ad)
        assert result.metadata.get("findmy_mode") is True
        assert result.metadata.get("serial_number") == "SN123456"

    def test_rejects_low_protocol(self, parser):
        body = bytes([0xE0, 1, 0x01])
        ad = _make_ad(manufacturer_data=self._navimow_mfr(body))
        assert parser.parse(ad) is None


# ---- Orbit B-hyve ----------------------------------------------------------

class TestOrbitBhyve:
    @pytest.fixture
    def parser(self):
        from adwatch.plugins.orbit_bhyve import OrbitBhyveParser
        return OrbitBhyveParser()

    def test_name_regex_match(self, parser):
        ad = _make_ad(local_name="bhyve_abc123")
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["device_id_suffix"] == "abc123"

    def test_vendor_uuid_match(self, parser):
        ad = _make_ad(service_uuids=["00000001-fe32-4f58-8b78-98e42b2c047f"])
        result = parser.parse(ad)
        assert result is not None
        assert result.device_class == "irrigation"

    def test_no_match(self, parser):
        assert parser.parse(_make_ad(local_name="random")) is None


# ---- Rainbird --------------------------------------------------------------

class TestRainbird:
    @pytest.fixture
    def parser(self):
        from adwatch.plugins.rainbird import RainbirdParser
        return RainbirdParser()

    def test_matches_rainbird_name(self, parser):
        ad = _make_ad(local_name="RAINBIRD_LNK2")
        result = parser.parse(ad)
        assert result.metadata["product_family"] == "LNK2/RC2"

    def test_bat_bt_name_with_zones(self, parser):
        ad = _make_ad(local_name="BAT-BT-8")
        result = parser.parse(ad)
        assert result.metadata["product_family"] == "ESP-BAT"
        assert result.metadata["zone_count"] == 8
        assert result.metadata["product_variant"] == "BAT-BT"


# ---- Greenworks ------------------------------------------------------------

class TestGreenworks:
    @pytest.fixture
    def parser(self):
        from adwatch.plugins.greenworks import GreenworksParser
        return GreenworksParser()

    def test_company_id_match(self, parser):
        ad = _make_ad(manufacturer_data=_mfr(0x15A8, b"\x00\x01"))
        result = parser.parse(ad)
        assert result is not None

    def test_greenworks_name(self, parser):
        ad = _make_ad(local_name="Greenworks Mower")
        result = parser.parse(ad)
        assert result.metadata["brand"] == "Greenworks"

    def test_cramer_name(self, parser):
        ad = _make_ad(local_name="Cramer 82V")
        result = parser.parse(ad)
        assert result.metadata["brand"] == "Cramer"

    def test_mac_oui_match(self, parser):
        ad = _make_ad(mac_address="34:12:AB:CD:EF:01")
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["mac_oui_match"] is True


# ---- Milwaukee -------------------------------------------------------------

class TestMilwaukeeOneKey:
    @pytest.fixture
    def parser(self):
        from adwatch.plugins.milwaukee_onekey import MilwaukeeOneKeyParser
        return MilwaukeeOneKeyParser()

    def test_matches_fdf5_uuid(self, parser):
        ad = _make_ad(service_uuids=["fdf5"])
        result = parser.parse(ad)
        assert result is not None
        assert result.device_class == "power_tool"

    def test_matches_company_id(self, parser):
        ad = _make_ad(manufacturer_data=_mfr(0x0604, b"\x01\x02\x03"))
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["payload_length"] == 3


# ---- Bosch -----------------------------------------------------------------

class TestBoschToolbox:
    @pytest.fixture
    def parser(self):
        from adwatch.plugins.bosch_toolbox import BoschToolboxParser
        return BoschToolboxParser()

    def test_matches_como_1_1_short_uuid(self, parser):
        ad = _make_ad(service_uuids=["fde8"])
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["family"] == "COMO_1.1_or_2.0"
        assert result.device_class == "power_tool"

    def test_matches_floodlight_helios(self, parser):
        ad = _make_ad(service_uuids=["30304c0d-511c-4e43-b701-09da37455430"])
        result = parser.parse(ad)
        assert result.metadata["family"] == "Helios"
        assert result.device_class == "floodlight"

    def test_no_match(self, parser):
        assert parser.parse(_make_ad()) is None
