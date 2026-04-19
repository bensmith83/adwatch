"""Tests for Nest / Google Home plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.nest import NestParser


@pytest.fixture
def parser():
    return NestParser()


def make_raw(service_data=None, service_uuids=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-05T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        manufacturer_data=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        service_data=service_data,
        service_uuids=service_uuids or [],
        **defaults,
    )


NEST_DATA = bytes.fromhex("1001000200e11900546313520066166401")


class TestNestParsing:
    def test_parse_valid_nest(self, parser):
        raw = make_raw(service_data={"feaf": NEST_DATA})
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(service_data={"feaf": NEST_DATA})
        result = parser.parse(raw)
        assert result.parser_name == "nest"

    def test_beacon_type(self, parser):
        raw = make_raw(service_data={"feaf": NEST_DATA})
        result = parser.parse(raw)
        assert result.beacon_type == "nest"

    def test_device_class_smart_home(self, parser):
        raw = make_raw(service_data={"feaf": NEST_DATA})
        result = parser.parse(raw)
        assert result.device_class == "smart_home"

    def test_identity_hash(self, parser):
        """Without local_name, identity falls back to SHA256(mac:service_data_hex)[:16]."""
        raw = make_raw(
            service_data={"feaf": NEST_DATA},
            mac_address="AA:BB:CC:DD:EE:FF",
        )
        result = parser.parse(raw)
        expected = hashlib.sha256(
            f"AA:BB:CC:DD:EE:FF:{NEST_DATA.hex()}".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_prefers_local_name_over_payload(self, parser):
        """When local_name is present, identity is SHA256(mac:local_name)[:16].

        The FEAF payload contains a rotating counter, so hashing it would
        change the identifier every emission and fragment a single device
        into many. The local_name (e.g. "NW3J0") is stable per device.
        """
        raw = make_raw(
            service_data={"feaf": NEST_DATA},
            local_name="NW3J0",
            mac_address="AA:BB:CC:DD:EE:FF",
        )
        result = parser.parse(raw)
        expected = hashlib.sha256(
            "AA:BB:CC:DD:EE:FF:NW3J0".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_stable_across_payload_rotation(self, parser):
        """Same device, same name, different payload counter → same identity."""
        payload_a = bytes.fromhex("1001000200e11900546313520066166401")
        payload_b = bytes.fromhex("1001000200e11900546313520066166402")
        raw_a = make_raw(service_data={"feaf": payload_a}, local_name="NW3J0")
        raw_b = make_raw(service_data={"feaf": payload_b}, local_name="NW3J0")
        assert parser.parse(raw_a).identifier_hash == parser.parse(raw_b).identifier_hash

    def test_identity_stable_across_modes(self, parser):
        """Same device seen with-payload and name-only → same identity."""
        with_data = make_raw(service_data={"feaf": NEST_DATA}, local_name="NW3J0")
        name_only = make_raw(service_uuids=["FEAF"], local_name="NW3J0")
        assert parser.parse(with_data).identifier_hash == parser.parse(name_only).identifier_hash

    def test_identity_hash_format(self, parser):
        raw = make_raw(service_data={"feaf": NEST_DATA})
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_raw_payload_hex(self, parser):
        raw = make_raw(service_data={"feaf": NEST_DATA})
        result = parser.parse(raw)
        assert result.raw_payload_hex == NEST_DATA.hex()

    def test_metadata_payload_hex(self, parser):
        raw = make_raw(service_data={"feaf": NEST_DATA})
        result = parser.parse(raw)
        assert result.metadata["payload_hex"] == NEST_DATA.hex()

    def test_metadata_payload_length(self, parser):
        raw = make_raw(service_data={"feaf": NEST_DATA})
        result = parser.parse(raw)
        assert result.metadata["payload_length"] == len(NEST_DATA)

    def test_no_storage(self, parser):
        assert parser.storage_schema() is None

    def test_has_ui(self, parser):
        cfg = parser.ui_config()
        assert cfg is not None
        assert cfg.tab_name == "Nest"

    def test_metadata_includes_local_name_hint(self, parser):
        """Metadata should include local_name if available."""
        raw = make_raw(service_data={"feaf": NEST_DATA}, local_name="NW3J0")
        result = parser.parse(raw)
        assert result.metadata["device_code"] == "NW3J0"

    def test_metadata_device_code_none(self, parser):
        raw = make_raw(service_data={"feaf": NEST_DATA})
        result = parser.parse(raw)
        assert result.metadata["device_code"] is None

    def test_api_router_without_db(self, parser):
        assert parser.api_router() is None

    def test_api_router_with_db(self, parser):
        router = parser.api_router(db=object())
        assert router is not None


class TestNestMalformed:
    def test_returns_none_no_service_data_no_uuid(self, parser):
        raw = make_raw(service_data=None)
        assert parser.parse(raw) is None

    def test_returns_none_wrong_uuid(self, parser):
        raw = make_raw(service_data={"abcd": NEST_DATA})
        assert parser.parse(raw) is None

    def test_returns_none_empty_data_no_uuid(self, parser):
        raw = make_raw(service_data={"feaf": b""})
        assert parser.parse(raw) is None


class TestNestNameOnly:
    """Nest devices sometimes advertise FEAF service UUID without service data.

    Observed in 2026-04-18 captures: `NW3J0` and `NJXAS` seen with
    ``service_uuids=["FEAF"]`` and empty service data (scan-response-only
    beacon). Should still identify as Nest.
    """

    def test_parses_feaf_uuid_without_service_data(self, parser):
        raw = make_raw(
            service_uuids=["FEAF"],
            local_name="NW3J0",
        )
        result = parser.parse(raw)
        assert result is not None
        assert result.beacon_type == "nest"
        assert result.device_class == "smart_home"

    def test_feaf_uuid_lowercase(self, parser):
        raw = make_raw(service_uuids=["feaf"], local_name="NJXAS")
        result = parser.parse(raw)
        assert result is not None

    def test_feaf_uuid_without_local_name(self, parser):
        """UUID alone is sufficient — FEAF is exclusively Nest Labs."""
        raw = make_raw(service_uuids=["FEAF"])
        result = parser.parse(raw)
        assert result is not None

    def test_name_only_metadata_records_device_code(self, parser):
        raw = make_raw(service_uuids=["FEAF"], local_name="NW3J0")
        result = parser.parse(raw)
        assert result.metadata["device_code"] == "NW3J0"

    def test_name_only_payload_empty(self, parser):
        raw = make_raw(service_uuids=["FEAF"], local_name="NW3J0")
        result = parser.parse(raw)
        assert result.raw_payload_hex == ""
        assert result.metadata["payload_length"] == 0

    def test_name_only_identity_hash_uses_mac_and_name(self, parser):
        """Without service data, identity falls back to mac+name to keep
        different co-located Nest devices distinguishable."""
        raw = make_raw(
            service_uuids=["FEAF"],
            local_name="NW3J0",
            mac_address="AA:BB:CC:DD:EE:FF",
        )
        result = parser.parse(raw)
        expected = hashlib.sha256(
            "AA:BB:CC:DD:EE:FF:NW3J0".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_service_data_still_preferred(self, parser):
        """If service_data is present, its payload still drives the hash/payload."""
        raw = make_raw(
            service_data={"feaf": NEST_DATA},
            service_uuids=["FEAF"],
        )
        result = parser.parse(raw)
        assert result.raw_payload_hex == NEST_DATA.hex()

    def test_empty_service_data_falls_through_when_uuid_present(self, parser):
        """Empty service_data + UUID in service_uuids → name-only branch.

        BlueZ occasionally surfaces a present-but-empty service_data entry
        alongside the UUID in service_uuids. Treat it like the name-only case
        rather than returning None.
        """
        raw = make_raw(
            service_data={"feaf": b""},
            service_uuids=["FEAF"],
            local_name="NW3J0",
        )
        result = parser.parse(raw)
        assert result is not None
        assert result.beacon_type == "nest"
        assert result.raw_payload_hex == ""

    def test_feaf_uuid_full_128_bit_form(self, parser):
        """BlueZ on Linux reports UUIDs as full 128-bit strings."""
        raw = make_raw(
            service_uuids=["0000feaf-0000-1000-8000-00805f9b34fb"],
            local_name="NW3J0",
        )
        result = parser.parse(raw)
        assert result is not None
        assert result.beacon_type == "nest"

    def test_service_data_full_128_bit_key(self, parser):
        """Service data dict keyed by full 128-bit UUID is also matched."""
        raw = make_raw(
            service_data={"0000feaf-0000-1000-8000-00805f9b34fb": NEST_DATA},
        )
        result = parser.parse(raw)
        assert result is not None
        assert result.raw_payload_hex == NEST_DATA.hex()
