"""Tests for Dreame robot vacuum BLE advertisement plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.dreame import DreameParser, DREAME_SERVICE_UUID, DREAME_NAME_RE


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


def _make_registry():
    registry = ParserRegistry()

    @register_parser(
        name="dreame",
        service_uuid=DREAME_SERVICE_UUID,
        local_name_pattern=r"^DL-",
        description="Dreame robot vacuum advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(DreameParser):
        pass

    return registry


class TestDreameMatching:
    def test_matches_service_uuid(self):
        """Matches on Dreame service UUID FD92."""
        registry = _make_registry()
        ad = _make_ad(
            service_uuids=["0000fd92-0000-1000-8000-00805f9b34fb"],
            local_name="DL-1102102677",
        )
        matches = registry.match(ad)
        assert len(matches) == 1

    def test_matches_local_name(self):
        """Matches on DL- prefix."""
        registry = _make_registry()
        ad = _make_ad(local_name="DL-1102102677")
        matches = registry.match(ad)
        assert len(matches) == 1

    def test_no_match_unrelated(self):
        """Does not match unrelated devices."""
        parser = DreameParser()
        ad = _make_ad(local_name="SomeDevice")
        result = parser.parse(ad)
        assert result is None


class TestDreameParsing:
    def test_parse_basic(self):
        """Parses Dreame vacuum advertisement."""
        parser = DreameParser()
        ad = _make_ad(
            local_name="DL-1102102677",
            service_uuids=["0000fd92-0000-1000-8000-00805f9b34fb"],
        )
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "dreame"
        assert result.beacon_type == "dreame"
        assert result.device_class == "vacuum"

    def test_serial_from_name(self):
        """Serial number extracted from local name."""
        parser = DreameParser()
        ad = _make_ad(
            local_name="DL-1102102677",
            service_uuids=["0000fd92-0000-1000-8000-00805f9b34fb"],
        )
        result = parser.parse(ad)
        assert result.metadata["serial"] == "1102102677"

    def test_device_name_in_metadata(self):
        """Full device name stored in metadata."""
        parser = DreameParser()
        ad = _make_ad(
            local_name="DL-1102102677",
            service_uuids=["0000fd92-0000-1000-8000-00805f9b34fb"],
        )
        result = parser.parse(ad)
        assert result.metadata["device_name"] == "DL-1102102677"

    def test_identity_hash(self):
        """Identity hash is SHA256('dreame:{mac}')[:16]."""
        mac = "11:22:33:44:55:66"
        parser = DreameParser()
        ad = _make_ad(
            local_name="DL-1102102677",
            service_uuids=["0000fd92-0000-1000-8000-00805f9b34fb"],
            mac_address=mac,
        )
        result = parser.parse(ad)
        expected = hashlib.sha256(f"dreame:{mac}".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_uuid_only_match(self):
        """Matches on UUID alone."""
        parser = DreameParser()
        ad = _make_ad(
            service_uuids=["0000fd92-0000-1000-8000-00805f9b34fb"],
        )
        result = parser.parse(ad)
        assert result is not None

    def test_name_only_match(self):
        """Matches on DL- name alone."""
        parser = DreameParser()
        ad = _make_ad(local_name="DL-1102102677")
        result = parser.parse(ad)
        assert result is not None

    def test_no_match_without_name_or_uuid(self):
        """Returns None without matching name or UUID."""
        parser = DreameParser()
        ad = _make_ad()
        result = parser.parse(ad)
        assert result is None


class TestDreameMiIO:
    """v1.1.0: Mi/MiIO service-UUID + dreame/mova service-data prefix."""

    def _parse(self, **kwargs):
        from adwatch.plugins.dreame import DreameParser
        defaults = {"timestamp": "2025-01-01T00:00:00Z",
                    "mac_address": "AA:BB:CC:DD:EE:FF",
                    "address_type": "random",
                    "manufacturer_data": None, "service_data": None}
        defaults.update(kwargs)
        return DreameParser().parse(RawAdvertisement(**defaults))

    def test_dreame_miio_service_data(self):
        result = self._parse(
            service_uuids=["fe98"],
            service_data={"fe98": b"dreame-L10"},
        )
        assert result is not None
        assert result.metadata["brand"] == "dreame"
        assert result.metadata["product_path"] == "miio_provisioning"
        assert result.metadata["provisioning_mode"] is True

    def test_mova_miio_service_data(self):
        result = self._parse(
            service_uuids=["fe98"],
            service_data={"fe98": b"mova-K20"},
        )
        assert result is not None
        assert result.metadata["brand"] == "mova"
        assert result.device_class == "lawn_mower"

    def test_miio_uuid_without_brand_prefix_returns_none(self):
        # FE98 + non-Dreame ASCII → not Dreame.
        result = self._parse(
            service_uuids=["fe98"],
            service_data={"fe98": b"xiaomi-band"},
        )
        assert result is None

    def test_miio_uuid_with_no_service_data_returns_none(self):
        result = self._parse(service_uuids=["fe98"])
        assert result is None

    def test_case_insensitive_prefix(self):
        result = self._parse(
            service_uuids=["fe98"],
            service_data={"fe98": b"DREAME-X11"},
        )
        assert result is not None
        assert result.metadata["brand"] == "dreame"
