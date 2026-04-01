"""Tests for Acaia coffee scale BLE plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.acaia_scale import AcaiaScaleParser


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
        name="acaia_scale",
        local_name_pattern=r"(?i)^(ACAIA|LUNAR|PEARL|PYXIS|CINCO)",
        description="Acaia coffee scale advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(AcaiaScaleParser):
        pass

    return registry


class TestAcaiaScaleRegistry:
    def test_matches_local_name_lunar(self):
        """Matches on local_name starting with LUNAR."""
        registry = _make_registry()
        ad = _make_ad(local_name="LUNAR_ABC123")
        matches = registry.match(ad)
        assert len(matches) >= 1

    def test_matches_local_name_acaia(self):
        """Matches on local_name starting with ACAIA."""
        registry = _make_registry()
        ad = _make_ad(local_name="ACAIA_XYZ")
        matches = registry.match(ad)
        assert len(matches) >= 1


class TestAcaiaScaleParser:
    def test_parser_name(self):
        """parser_name is 'acaia_scale'."""
        parser = AcaiaScaleParser()
        ad = _make_ad(local_name="LUNAR_ABC123")
        result = parser.parse(ad)
        assert result.parser_name == "acaia_scale"

    def test_beacon_type(self):
        """beacon_type is 'acaia_scale'."""
        parser = AcaiaScaleParser()
        ad = _make_ad(local_name="LUNAR_ABC123")
        result = parser.parse(ad)
        assert result.beacon_type == "acaia_scale"

    def test_device_class_scale(self):
        """device_class is 'scale'."""
        parser = AcaiaScaleParser()
        ad = _make_ad(local_name="LUNAR_ABC123")
        result = parser.parse(ad)
        assert result.device_class == "scale"

    # --- Model detection from local_name ---

    def test_model_lunar(self):
        """LUNAR_ABC123 -> model='Lunar'."""
        parser = AcaiaScaleParser()
        ad = _make_ad(local_name="LUNAR_ABC123")
        result = parser.parse(ad)
        assert result.metadata["model"] == "Lunar"

    def test_model_pearl_s(self):
        """PEARLS_DEF456 -> model='Pearl S'."""
        parser = AcaiaScaleParser()
        ad = _make_ad(local_name="PEARLS_DEF456")
        result = parser.parse(ad)
        assert result.metadata["model"] == "Pearl S"

    def test_model_pearl(self):
        """PEARL_GHI789 -> model='Pearl'."""
        parser = AcaiaScaleParser()
        ad = _make_ad(local_name="PEARL_GHI789")
        result = parser.parse(ad)
        assert result.metadata["model"] == "Pearl"

    def test_model_pyxis(self):
        """PYXIS_JKL012 -> model='Pyxis'."""
        parser = AcaiaScaleParser()
        ad = _make_ad(local_name="PYXIS_JKL012")
        result = parser.parse(ad)
        assert result.metadata["model"] == "Pyxis"

    def test_model_cinco(self):
        """CINCO_MNO345 -> model='Cinco'."""
        parser = AcaiaScaleParser()
        ad = _make_ad(local_name="CINCO_MNO345")
        result = parser.parse(ad)
        assert result.metadata["model"] == "Cinco"

    def test_model_acaia_generic(self):
        """ACAIA_PQR678 -> model='Acaia'."""
        parser = AcaiaScaleParser()
        ad = _make_ad(local_name="ACAIA_PQR678")
        result = parser.parse(ad)
        assert result.metadata["model"] == "Acaia"

    # --- Device ID extraction ---

    def test_device_id_from_local_name(self):
        """LUNAR_ABC123 -> device_id='ABC123'."""
        parser = AcaiaScaleParser()
        ad = _make_ad(local_name="LUNAR_ABC123")
        result = parser.parse(ad)
        assert result.metadata["device_id"] == "ABC123"

    def test_device_id_with_space_separator(self):
        """LUNAR ABC123 -> device_id='ABC123'."""
        parser = AcaiaScaleParser()
        ad = _make_ad(local_name="LUNAR ABC123")
        result = parser.parse(ad)
        assert result.metadata["device_id"] == "ABC123"

    def test_no_device_id_no_separator(self):
        """LUNAR (no separator) -> device_id not in metadata or is None."""
        parser = AcaiaScaleParser()
        ad = _make_ad(local_name="LUNAR")
        result = parser.parse(ad)
        assert result.metadata.get("device_id") is None

    # --- local_name in metadata ---

    def test_local_name_in_metadata(self):
        """metadata['local_name'] is set to the raw local_name."""
        parser = AcaiaScaleParser()
        ad = _make_ad(local_name="LUNAR_ABC123")
        result = parser.parse(ad)
        assert result.metadata["local_name"] == "LUNAR_ABC123"

    # --- Identity hash ---

    def test_identity_hash(self):
        """Identity hash is SHA256(mac:acaia_scale)[:16]."""
        mac = "11:22:33:44:55:66"
        parser = AcaiaScaleParser()
        ad = _make_ad(local_name="LUNAR_ABC123", mac_address=mac)
        result = parser.parse(ad)
        expected = hashlib.sha256(f"{mac}:acaia_scale".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    # --- raw_payload_hex ---

    def test_raw_payload_hex_with_manufacturer_data(self):
        """raw_payload_hex is hex of manufacturer payload if present."""
        parser = AcaiaScaleParser()
        mfr_data = b"\x01\x02\xDE\xAD\xBE\xEF"
        ad = _make_ad(local_name="LUNAR_ABC123", manufacturer_data=mfr_data)
        result = parser.parse(ad)
        assert result.raw_payload_hex == mfr_data.hex()

    def test_raw_payload_hex_empty_without_manufacturer_data(self):
        """raw_payload_hex is '' when no manufacturer_data."""
        parser = AcaiaScaleParser()
        ad = _make_ad(local_name="LUNAR_ABC123")
        result = parser.parse(ad)
        assert result.raw_payload_hex == ""

    # --- Edge cases ---

    def test_returns_none_for_none_local_name(self):
        """Returns None when local_name is None."""
        parser = AcaiaScaleParser()
        ad = _make_ad(local_name=None)
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_for_non_matching_local_name(self):
        """Returns None for local_name that doesn't match Acaia patterns."""
        parser = AcaiaScaleParser()
        ad = _make_ad(local_name="SomeOtherDevice")
        result = parser.parse(ad)
        assert result is None

    def test_works_without_manufacturer_data(self):
        """Returns valid result with no manufacturer_data."""
        parser = AcaiaScaleParser()
        ad = _make_ad(local_name="LUNAR_ABC123")
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "acaia_scale"
        assert result.raw_payload_hex == ""

    def test_case_insensitive_matching(self):
        """Case insensitive: 'lunar_abc' matches and model='Lunar'."""
        parser = AcaiaScaleParser()
        ad = _make_ad(local_name="lunar_abc")
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "acaia_scale"
        assert result.metadata["model"] == "Lunar"
