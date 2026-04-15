"""Tests for Midea smart-appliance plugin."""

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.midea_appliance import MideaApplianceParser


@pytest.fixture
def parser():
    return MideaApplianceParser()


def make_raw(manufacturer_data=None, local_name=None, **kwargs):
    defaults = dict(
        timestamp="2026-04-15T00:00:00+00:00",
        mac_address="41:1C:32:B7:18:A5",
        address_type="random",
        service_data=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        manufacturer_data=manufacturer_data,
        service_uuids=[],
        local_name=local_name,
        **defaults,
    )


SHORT_MFR = bytes.fromhex("a806013030303030513135414331384236")
LONG_MFR = bytes.fromhex(
    "a80601303030303051313541433138423601411c32b718a574b85400"
)
SERIAL = "00000Q15AC18B6"


class TestMideaParsing:
    def test_parses_short_frame(self, parser):
        raw = make_raw(manufacturer_data=SHORT_MFR, local_name="net")
        result = parser.parse(raw)
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(manufacturer_data=SHORT_MFR, local_name="net")
        result = parser.parse(raw)
        assert result.parser_name == "midea_appliance"

    def test_beacon_type(self, parser):
        raw = make_raw(manufacturer_data=SHORT_MFR, local_name="net")
        result = parser.parse(raw)
        assert result.beacon_type == "midea_appliance"

    def test_device_class(self, parser):
        raw = make_raw(manufacturer_data=SHORT_MFR, local_name="net")
        result = parser.parse(raw)
        assert result.device_class == "appliance"

    def test_extracts_serial_short(self, parser):
        raw = make_raw(manufacturer_data=SHORT_MFR, local_name="net")
        result = parser.parse(raw)
        assert result.metadata["serial_number"] == SERIAL

    def test_extracts_serial_long(self, parser):
        raw = make_raw(manufacturer_data=LONG_MFR, local_name="net")
        result = parser.parse(raw)
        assert result.metadata["serial_number"] == SERIAL

    def test_extracts_family_code(self, parser):
        raw = make_raw(manufacturer_data=SHORT_MFR, local_name="net")
        result = parser.parse(raw)
        assert result.metadata["family_code"] == "Q"

    def test_extracts_setup_mode(self, parser):
        raw = make_raw(manufacturer_data=SHORT_MFR, local_name="net")
        result = parser.parse(raw)
        assert result.metadata["setup_mode"] is True

    def test_long_frame_extracts_bd_addr(self, parser):
        raw = make_raw(manufacturer_data=LONG_MFR, local_name="net")
        result = parser.parse(raw)
        assert result.metadata["embedded_bd_addr"] == "41:1C:32:B7:18:A5"

    def test_short_frame_no_bd_addr(self, parser):
        raw = make_raw(manufacturer_data=SHORT_MFR, local_name="net")
        result = parser.parse(raw)
        assert "embedded_bd_addr" not in result.metadata

    def test_identifier_hash_stable_across_frames(self, parser):
        short = parser.parse(make_raw(manufacturer_data=SHORT_MFR, local_name="net"))
        long_ = parser.parse(make_raw(manufacturer_data=LONG_MFR, local_name="net"))
        assert short.identifier_hash == long_.identifier_hash

    def test_identifier_hash_format(self, parser):
        raw = make_raw(manufacturer_data=SHORT_MFR, local_name="net")
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)


class TestMideaNonMatching:
    def test_returns_none_when_no_mfg_data(self, parser):
        raw = make_raw()
        assert parser.parse(raw) is None

    def test_returns_none_for_other_company_id(self, parser):
        raw = make_raw(
            manufacturer_data=bytes.fromhex("4c0002150000000000"),
            local_name="net",
        )
        assert parser.parse(raw) is None

    def test_returns_none_for_unknown_frame_type(self, parser):
        raw = make_raw(
            manufacturer_data=bytes.fromhex(
                "a806ff3030303030305131354143313842363601"
            ),
            local_name="net",
        )
        assert parser.parse(raw) is None

    def test_returns_none_for_truncated_payload(self, parser):
        raw = make_raw(manufacturer_data=bytes.fromhex("a80601303030"), local_name="net")
        assert parser.parse(raw) is None

    def test_matches_without_local_name(self, parser):
        raw = make_raw(manufacturer_data=SHORT_MFR, local_name=None)
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata.get("setup_mode") is False
