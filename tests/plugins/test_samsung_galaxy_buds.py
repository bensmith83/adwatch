"""Tests for Samsung Galaxy Buds plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.samsung_galaxy_buds import SamsungGalaxyBudsParser


@pytest.fixture
def parser():
    return SamsungGalaxyBudsParser()


def make_raw(manufacturer_data=None, service_data=None, service_uuids=None, local_name=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-05T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        manufacturer_data=manufacturer_data,
        service_data=service_data,
        service_uuids=service_uuids or [],
        local_name=local_name,
        **defaults,
    )


# Real sample from CSV
BUDS3_PRO_SVC_DATA = bytes.fromhex("005fe6f74080c94e5ded74a54e4000")
BUDS3_PRO_NAME = "Galaxy Buds3 Pro (E757) LE"


class TestSamsungGalaxyBudsParsing:
    def test_parse_valid_service_data(self, parser):
        raw = make_raw(
            service_data={"fd69": BUDS3_PRO_SVC_DATA},
            local_name=BUDS3_PRO_NAME,
        )
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(
            service_data={"fd69": BUDS3_PRO_SVC_DATA},
            local_name=BUDS3_PRO_NAME,
        )
        result = parser.parse(raw)
        assert result.parser_name == "samsung_galaxy_buds"

    def test_beacon_type(self, parser):
        raw = make_raw(
            service_data={"fd69": BUDS3_PRO_SVC_DATA},
            local_name=BUDS3_PRO_NAME,
        )
        result = parser.parse(raw)
        assert result.beacon_type == "samsung_galaxy_buds"

    def test_device_class_earbuds(self, parser):
        raw = make_raw(
            service_data={"fd69": BUDS3_PRO_SVC_DATA},
            local_name=BUDS3_PRO_NAME,
        )
        result = parser.parse(raw)
        assert result.device_class == "earbuds"

    def test_identity_hash_format(self, parser):
        raw = make_raw(
            service_data={"fd69": BUDS3_PRO_SVC_DATA},
            local_name=BUDS3_PRO_NAME,
        )
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        assert all(c in "0123456789abcdef" for c in result.identifier_hash)

    def test_raw_payload_hex(self, parser):
        raw = make_raw(
            service_data={"fd69": BUDS3_PRO_SVC_DATA},
            local_name=BUDS3_PRO_NAME,
        )
        result = parser.parse(raw)
        assert result.raw_payload_hex == BUDS3_PRO_SVC_DATA.hex()


class TestSamsungGalaxyBudsServiceData:
    def test_frame_type_extracted(self, parser):
        raw = make_raw(
            service_data={"fd69": BUDS3_PRO_SVC_DATA},
            local_name=BUDS3_PRO_NAME,
        )
        result = parser.parse(raw)
        assert result.metadata["frame_type"] == 0x00

    def test_device_id_extracted(self, parser):
        raw = make_raw(
            service_data={"fd69": BUDS3_PRO_SVC_DATA},
            local_name=BUDS3_PRO_NAME,
        )
        result = parser.parse(raw)
        assert result.metadata["device_id"] == 0x5FE6

    def test_flags_extracted(self, parser):
        raw = make_raw(
            service_data={"fd69": BUDS3_PRO_SVC_DATA},
            local_name=BUDS3_PRO_NAME,
        )
        result = parser.parse(raw)
        assert result.metadata["flags"] == 0xF7


class TestSamsungGalaxyBudsModelExtraction:
    def test_model_from_buds3_pro_name(self, parser):
        raw = make_raw(
            service_data={"fd69": BUDS3_PRO_SVC_DATA},
            local_name="Galaxy Buds3 Pro (E757) LE",
        )
        result = parser.parse(raw)
        assert result.metadata["model"] == "Galaxy Buds3 Pro"

    def test_model_from_buds2_pro_name(self, parser):
        raw = make_raw(
            service_data={"fd69": BUDS3_PRO_SVC_DATA},
            local_name="Galaxy Buds2 Pro (A1B2) LE",
        )
        result = parser.parse(raw)
        assert result.metadata["model"] == "Galaxy Buds2 Pro"

    def test_model_from_buds_fe_name(self, parser):
        raw = make_raw(
            service_data={"fd69": BUDS3_PRO_SVC_DATA},
            local_name="Galaxy Buds FE (C3D4) LE",
        )
        result = parser.parse(raw)
        assert result.metadata["model"] == "Galaxy Buds FE"

    def test_model_from_buds_live_name(self, parser):
        raw = make_raw(
            service_data={"fd69": BUDS3_PRO_SVC_DATA},
            local_name="Galaxy Buds Live (E5F6) LE",
        )
        result = parser.parse(raw)
        assert result.metadata["model"] == "Galaxy Buds Live"

    def test_no_model_without_local_name(self, parser):
        raw = make_raw(service_data={"fd69": BUDS3_PRO_SVC_DATA})
        result = parser.parse(raw)
        assert result is not None
        assert "model" not in result.metadata


class TestSamsungGalaxyBudsMatching:
    def test_match_on_service_data_only(self, parser):
        """Should parse with just fd69 service data, no local_name."""
        raw = make_raw(service_data={"fd69": BUDS3_PRO_SVC_DATA})
        result = parser.parse(raw)
        assert result is not None

    def test_match_on_local_name_only(self, parser):
        """Should parse with just Galaxy Buds local_name, no service data."""
        raw = make_raw(local_name="Galaxy Buds3 Pro (E757) LE")
        result = parser.parse(raw)
        assert result is not None

    def test_returns_none_no_match(self, parser):
        """No fd69 service data and no Galaxy Buds name."""
        raw = make_raw(local_name="Some Other Device")
        assert parser.parse(raw) is None

    def test_returns_none_empty(self, parser):
        """No data at all."""
        raw = make_raw()
        assert parser.parse(raw) is None

    def test_returns_none_wrong_service_uuid(self, parser):
        """Service data for a different UUID should not match."""
        raw = make_raw(service_data={"abcd": b"\x00\x01\x02"})
        assert parser.parse(raw) is None


class TestSamsungGalaxyBudsIdentity:
    def test_different_mac_different_hash(self, parser):
        r1 = parser.parse(make_raw(
            service_data={"fd69": BUDS3_PRO_SVC_DATA},
            mac_address="AA:BB:CC:DD:EE:FF",
        ))
        r2 = parser.parse(make_raw(
            service_data={"fd69": BUDS3_PRO_SVC_DATA},
            mac_address="11:22:33:44:55:66",
        ))
        assert r1.identifier_hash != r2.identifier_hash

    def test_same_mac_same_hash(self, parser):
        r1 = parser.parse(make_raw(
            service_data={"fd69": BUDS3_PRO_SVC_DATA},
            local_name="Galaxy Buds3 Pro (E757) LE",
        ))
        r2 = parser.parse(make_raw(
            service_data={"fd69": BUDS3_PRO_SVC_DATA},
            local_name="Galaxy Buds3 Pro (E757) LE",
        ))
        assert r1.identifier_hash == r2.identifier_hash
