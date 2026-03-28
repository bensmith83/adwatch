"""Tests for Apple Continuity parser routing fix (types 0x01 and 0x16)."""

from adwatch.models import RawAdvertisement
from adwatch.parsers.apple_continuity import AppleContinuityParser


def _apple_mfr_data(tlv_type, tlv_len, tlv_value):
    """Build Apple manufacturer data: company_id (0x004C LE) + type + len + value."""
    return b"\x4c\x00" + bytes([tlv_type, tlv_len]) + tlv_value


def _make_ad(mfr_data):
    return RawAdvertisement(
        timestamp="2026-03-27T00:00:00Z",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        manufacturer_data=mfr_data,
        service_data=None,
    )


class TestOverflowAreaRouting:
    """Type 0x01 should route to _parse_overflow_area, not _parse_unknown."""

    def test_overflow_area_beacon_type(self):
        mfr_data = _apple_mfr_data(0x01, 16, b"\x00" * 16)
        result = AppleContinuityParser().parse(_make_ad(mfr_data))
        assert result is not None
        assert result.beacon_type == "apple_overflow_area", (
            f"Expected 'apple_overflow_area', got '{result.beacon_type}'"
        )

    def test_overflow_area_has_data_field(self):
        payload = b"\xAB\xCD" + b"\x00" * 14
        mfr_data = _apple_mfr_data(0x01, 16, payload)
        result = AppleContinuityParser().parse(_make_ad(mfr_data))
        assert result is not None
        assert "data" in result.metadata, (
            f"Expected 'data' key in metadata, got keys: {list(result.metadata.keys())}"
        )
        assert result.metadata["data"] == payload.hex()


class TestTetheringSourceAltRouting:
    """Type 0x16 should route to _parse_tethering, not _parse_unknown."""

    def test_tethering_source_alt_beacon_type(self):
        mfr_data = _apple_mfr_data(0x16, 8, b"\x08\x64" + b"\x00" * 6)
        result = AppleContinuityParser().parse(_make_ad(mfr_data))
        assert result is not None
        assert result.beacon_type == "apple_tethering_source_alt", (
            f"Expected 'apple_tethering_source_alt', got '{result.beacon_type}'"
        )

    def test_tethering_source_alt_extracts_signal_and_battery(self):
        mfr_data = _apple_mfr_data(0x16, 8, b"\x08\x64" + b"\x00" * 6)
        result = AppleContinuityParser().parse(_make_ad(mfr_data))
        assert result is not None
        assert result.metadata.get("signal_strength") == 0x08, (
            f"Expected signal_strength=8, got {result.metadata.get('signal_strength')}"
        )
        assert result.metadata.get("battery") == 0x64, (
            f"Expected battery=100, got {result.metadata.get('battery')}"
        )

    def test_tethering_source_alt_short_payload_returns_none(self):
        # < 2 bytes payload should return None from _parse_tethering guard
        mfr_data = _apple_mfr_data(0x16, 1, b"\x08")
        result = AppleContinuityParser().parse(_make_ad(mfr_data))
        assert result is None


class TestRegressionExistingRoutes:
    """Existing routes must not break."""

    def test_nearby_info_still_works(self):
        # Type 0x10, need >= 3 bytes payload
        mfr_data = _apple_mfr_data(0x10, 5, b"\x07\x0A\xAB\xCD\xEF")
        result = AppleContinuityParser().parse(_make_ad(mfr_data))
        assert result is not None
        assert result.beacon_type == "apple_nearby"

    def test_handoff_still_works(self):
        # Type 0x0C
        mfr_data = _apple_mfr_data(0x0C, 4, b"\x08\x01\x02\x03")
        result = AppleContinuityParser().parse(_make_ad(mfr_data))
        assert result is not None
        assert result.beacon_type == "apple_handoff"
