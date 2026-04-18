"""Tests for batch 2 pending plugins: tesla, tractive, traeger, freestyle_libre3."""

import hashlib

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


# ---- Tesla -----------------------------------------------------------------

class TestTesla:
    @pytest.fixture
    def parser(self):
        from adwatch.plugins.tesla import TeslaParser
        return TeslaParser()

    def test_matches_service_uuid(self, parser):
        ad = _make_ad(service_uuids=["1122"])
        assert parser.parse(ad) is not None

    def test_matches_name_model_y(self, parser):
        # Per passive report, the model char is at index 3 (the 4th character).
        ad = _make_ad(local_name="SabYxxxxxxx")
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["model"] == "Model Y"

    def test_model_3(self, parser):
        ad = _make_ad(local_name="Sab3xxxx")
        assert parser.parse(ad).metadata["model"] == "Model 3"

    def test_model_s(self, parser):
        ad = _make_ad(local_name="SabSxxxx")
        assert parser.parse(ad).metadata["model"] == "Model S"

    def test_vin_hash_fragment(self, parser):
        ad = _make_ad(local_name="SabYDEADBEEF")
        result = parser.parse(ad)
        assert result.metadata["vin_hash_fragment"] == "YDEADBEEF"

    def test_identity_hash_uses_vin_hash(self, parser):
        ad = _make_ad(local_name="SabYDEADBEEF")
        result = parser.parse(ad)
        expected = hashlib.sha256("tesla:YDEADBEEF".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_device_class(self, parser):
        ad = _make_ad(service_uuids=["1122"])
        assert parser.parse(ad).device_class == "vehicle"

    def test_no_match(self, parser):
        assert parser.parse(_make_ad(local_name="Random")) is None

    @pytest.mark.parametrize("name", [
        "Sonos Arc",
        "Samsung Galaxy",
        "Surface Laptop",
        "Sensor42",
        "Speaker-01",
    ])
    def test_rejects_non_tesla_s_prefix(self, parser, name):
        # Position-3 char is not a recognized Tesla model char (3/Y/S/X/C/R/D/P).
        assert parser.parse(_make_ad(local_name=name)) is None


# ---- Tractive --------------------------------------------------------------

class TestTractive:
    @pytest.fixture
    def parser(self):
        from adwatch.plugins.tractive import TractiveParser
        return TractiveParser()

    def test_matches_dog_uuid(self, parser):
        from adwatch.plugins.tractive import SERVICE_UUID_DOG
        ad = _make_ad(service_uuids=[SERVICE_UUID_DOG])
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["family"] == "Dog"

    def test_matches_cat_uuid(self, parser):
        from adwatch.plugins.tractive import SERVICE_UUID_CAT
        result = parser.parse(_make_ad(service_uuids=[SERVICE_UUID_CAT]))
        assert result.metadata["family"] == "Cat"

    def test_matches_v2_uuid(self, parser):
        from adwatch.plugins.tractive import SERVICE_UUID_V2
        result = parser.parse(_make_ad(service_uuids=[SERVICE_UUID_V2]))
        assert result.metadata["family"] == "V2"

    def test_matches_fw4_uuid(self, parser):
        from adwatch.plugins.tractive import SERVICE_UUID_FW4
        result = parser.parse(_make_ad(service_uuids=[SERVICE_UUID_FW4]))
        assert result.metadata["family"] == "Fw4"

    def test_dfu_mode_name(self, parser):
        result = parser.parse(_make_ad(local_name="TG7A"))
        assert result.metadata["dfu_active"] is True
        assert result.metadata["dfu_model_code"] == "TG7A"

    def test_dfu_all_12_names_match(self, parser):
        from adwatch.plugins.tractive import DFU_NAMES
        for n in DFU_NAMES:
            result = parser.parse(_make_ad(local_name=n))
            assert result is not None, f"{n} did not match"

    def test_device_class(self, parser):
        from adwatch.plugins.tractive import SERVICE_UUID_DOG
        assert parser.parse(_make_ad(service_uuids=[SERVICE_UUID_DOG])).device_class == "pet_tracker"

    def test_no_match(self, parser):
        assert parser.parse(_make_ad(local_name="NotATracker")) is None


# ---- Traeger ---------------------------------------------------------------

class TestTraeger:
    @pytest.fixture
    def parser(self):
        from adwatch.plugins.traeger import TraegerParser
        return TraegerParser()

    def test_matches_yosemite_name(self, parser):
        result = parser.parse(_make_ad(local_name="Yosemite_abc123"))
        assert result is not None
        assert result.metadata["provisioning_mode"] is True

    def test_matches_service_uuid(self, parser):
        from adwatch.plugins.traeger import TRAEGER_PROVISIONING_SERVICE_UUID
        result = parser.parse(
            _make_ad(service_uuids=[TRAEGER_PROVISIONING_SERVICE_UUID])
        )
        assert result is not None

    def test_device_class_appliance(self, parser):
        assert parser.parse(_make_ad(local_name="Yosemite")).device_class == "appliance"

    def test_no_match(self, parser):
        assert parser.parse(_make_ad(local_name="not-a-grill")) is None


# ---- FreeStyle Libre 3 -----------------------------------------------------

class TestFreeStyleLibre3:
    @pytest.fixture
    def parser(self):
        from adwatch.plugins.freestyle_libre3 import FreeStyleLibre3Parser
        return FreeStyleLibre3Parser()

    def test_matches_freestyle_libre_3_name(self, parser):
        result = parser.parse(_make_ad(local_name="FreeStyle Libre 3"))
        assert result is not None
        assert result.metadata["model"] == "FreeStyle Libre 3"

    def test_matches_abbott_libre_uuid(self, parser):
        ad = _make_ad(service_uuids=["08981482-ef89-11e9-81b4-2a2ae2dbcce4"])
        result = parser.parse(ad)
        assert result is not None
        assert "abbott_uuid" in result.metadata

    def test_device_class_medical(self, parser):
        assert parser.parse(_make_ad(local_name="LIBRE3")).device_class == "medical"

    def test_no_match(self, parser):
        assert parser.parse(_make_ad(local_name="Unrelated")) is None
