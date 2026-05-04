"""Tests for Garmin wearable BLE advertisement plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.garmin import GarminParser, GARMIN_COMPANY_ID


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
        name="garmin",
        company_id=GARMIN_COMPANY_ID,
        description="Garmin wearable advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(GarminParser):
        pass

    return registry


def _garmin_mfr_data(payload=b"\x01\x02\x03"):
    """Build manufacturer data: company_id (LE) + payload."""
    return GARMIN_COMPANY_ID.to_bytes(2, "little") + payload


class TestGarminParser:
    def test_matches_company_id_0x0087(self):
        """Matches on Garmin company_id 0x0087."""
        registry = _make_registry()
        ad = _make_ad(manufacturer_data=_garmin_mfr_data())
        matches = registry.match(ad)
        assert len(matches) >= 1

    def test_parser_name(self):
        """parser_name is 'garmin'."""
        parser = GarminParser()
        ad = _make_ad(manufacturer_data=_garmin_mfr_data())
        result = parser.parse(ad)
        assert result.parser_name == "garmin"

    def test_beacon_type(self):
        """beacon_type is 'garmin'."""
        parser = GarminParser()
        ad = _make_ad(manufacturer_data=_garmin_mfr_data())
        result = parser.parse(ad)
        assert result.beacon_type == "garmin"

    # --- Device class routing ---

    def test_device_class_default_wearable(self):
        """Default device_class is 'wearable' for watches."""
        parser = GarminParser()
        ad = _make_ad(
            manufacturer_data=_garmin_mfr_data(),
            local_name="Forerunner 265",
        )
        result = parser.parse(ad)
        assert result.device_class == "wearable"

    def test_device_class_heart_rate_monitor(self):
        """device_class is 'heart_rate_monitor' for HRM devices."""
        parser = GarminParser()
        ad = _make_ad(
            manufacturer_data=_garmin_mfr_data(),
            local_name="HRM-Pro",
        )
        result = parser.parse(ad)
        assert result.device_class == "heart_rate_monitor"

    def test_device_class_cycling_computer(self):
        """device_class is 'cycling_computer' for Edge devices."""
        parser = GarminParser()
        ad = _make_ad(
            manufacturer_data=_garmin_mfr_data(),
            local_name="Edge 840",
        )
        result = parser.parse(ad)
        assert result.device_class == "cycling_computer"

    def test_device_class_scale(self):
        """device_class is 'scale' for Index devices."""
        parser = GarminParser()
        ad = _make_ad(
            manufacturer_data=_garmin_mfr_data(),
            local_name="Index S2",
        )
        result = parser.parse(ad)
        assert result.device_class == "scale"

    # --- Device family extraction ---

    def test_device_family_forerunner(self):
        """Forerunner 265 -> device_family='Forerunner', model='Forerunner 265'."""
        parser = GarminParser()
        ad = _make_ad(
            manufacturer_data=_garmin_mfr_data(),
            local_name="Forerunner 265",
        )
        result = parser.parse(ad)
        assert result.metadata["device_family"] == "Forerunner"
        assert result.metadata["model"] == "Forerunner 265"

    def test_device_family_fenix(self):
        """fenix 7 -> device_family='Fenix' (capitalized)."""
        parser = GarminParser()
        ad = _make_ad(
            manufacturer_data=_garmin_mfr_data(),
            local_name="fenix 7",
        )
        result = parser.parse(ad)
        assert result.metadata["device_family"] == "Fenix"

    def test_device_family_venu(self):
        """Venu 3 -> device_family='Venu'."""
        parser = GarminParser()
        ad = _make_ad(
            manufacturer_data=_garmin_mfr_data(),
            local_name="Venu 3",
        )
        result = parser.parse(ad)
        assert result.metadata["device_family"] == "Venu"

    def test_device_family_hrm(self):
        """HRM-Pro -> device_family='HRM'."""
        parser = GarminParser()
        ad = _make_ad(
            manufacturer_data=_garmin_mfr_data(),
            local_name="HRM-Pro",
        )
        result = parser.parse(ad)
        assert result.metadata["device_family"] == "HRM"

    def test_device_family_edge(self):
        """Edge 840 -> device_family='Edge'."""
        parser = GarminParser()
        ad = _make_ad(
            manufacturer_data=_garmin_mfr_data(),
            local_name="Edge 840",
        )
        result = parser.parse(ad)
        assert result.metadata["device_family"] == "Edge"

    def test_device_family_vivoactive(self):
        """vivoactive 5 -> device_family='Vivoactive' (capitalized)."""
        parser = GarminParser()
        ad = _make_ad(
            manufacturer_data=_garmin_mfr_data(),
            local_name="vivoactive 5",
        )
        result = parser.parse(ad)
        assert result.metadata["device_family"] == "Vivoactive"

    def test_device_family_unknown_no_local_name(self):
        """None local_name -> device_family='Unknown'."""
        parser = GarminParser()
        ad = _make_ad(manufacturer_data=_garmin_mfr_data())
        result = parser.parse(ad)
        assert result.metadata["device_family"] == "Unknown"

    def test_device_family_unknown_empty_local_name(self):
        """Empty local_name -> device_family='Unknown'."""
        parser = GarminParser()
        ad = _make_ad(
            manufacturer_data=_garmin_mfr_data(),
            local_name="",
        )
        result = parser.parse(ad)
        assert result.metadata["device_family"] == "Unknown"

    # --- Message type ---

    def test_message_type_from_payload(self):
        """Byte 0 of payload (offset 2 in full mfr data) -> metadata['message_type']."""
        parser = GarminParser()
        ad = _make_ad(manufacturer_data=_garmin_mfr_data(payload=b"\x42\xAA\xBB"))
        result = parser.parse(ad)
        assert result.metadata["message_type"] == 0x42

    # --- Identity hash ---

    def test_identity_hash(self):
        """Identity hash is SHA256(mac_address:garmin)[:16]."""
        mac = "11:22:33:44:55:66"
        parser = GarminParser()
        ad = _make_ad(manufacturer_data=_garmin_mfr_data(), mac_address=mac)
        result = parser.parse(ad)
        expected = hashlib.sha256(f"{mac}:garmin".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    # --- raw_payload_hex ---

    def test_raw_payload_hex(self):
        """raw_payload_hex contains hex of manufacturer payload (without company_id)."""
        parser = GarminParser()
        payload = b"\xDE\xAD\xBE\xEF"
        ad = _make_ad(manufacturer_data=_garmin_mfr_data(payload=payload))
        result = parser.parse(ad)
        assert result.raw_payload_hex == payload.hex()

    # --- Edge cases ---

    def test_returns_none_wrong_company_id(self):
        """Returns None when company_id is not Garmin."""
        parser = GarminParser()
        data = (0x004C).to_bytes(2, "little") + b"\x01\x02\x03"
        ad = _make_ad(manufacturer_data=data)
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_no_manufacturer_data(self):
        """Returns None when manufacturer_data is None."""
        parser = GarminParser()
        ad = _make_ad()
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_short_data(self):
        """Returns None when manufacturer_data < 3 bytes (company_id only, no payload)."""
        parser = GarminParser()
        ad = _make_ad(manufacturer_data=GARMIN_COMPANY_ID.to_bytes(2, "little"))
        result = parser.parse(ad)
        assert result is None

    def test_handles_none_local_name_gracefully(self):
        """Parses successfully with local_name=None, family='Unknown'."""
        parser = GarminParser()
        ad = _make_ad(manufacturer_data=_garmin_mfr_data())
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["device_family"] == "Unknown"
        assert result.parser_name == "garmin"

    def test_returns_none_exact_two_bytes_company_id_only(self):
        """Exactly 2 bytes (company ID, no payload) returns None."""
        parser = GarminParser()
        ad = _make_ad(manufacturer_data=GARMIN_COMPANY_ID.to_bytes(2, "little"))
        result = parser.parse(ad)
        assert result is None

    def test_parses_minimum_three_byte_payload(self):
        """Exactly 3 bytes (company ID + 1 byte payload) parses successfully."""
        parser = GarminParser()
        ad = _make_ad(
            manufacturer_data=GARMIN_COMPANY_ID.to_bytes(2, "little") + b"\x42",
        )
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["message_type"] == 0x42


class TestGarminGFDI:
    """v1.2.0: GFDI control UUID for post-paired sightings."""

    def _parse(self, **kwargs):
        from adwatch.plugins.garmin import GarminParser
        defaults = {"timestamp": "2025-01-01T00:00:00Z",
                    "mac_address": "AA:BB:CC:DD:EE:FF",
                    "address_type": "random",
                    "manufacturer_data": None, "service_data": None}
        defaults.update(kwargs)
        return GarminParser().parse(RawAdvertisement(**defaults))

    def test_match_gfdi_uuid(self):
        from adwatch.plugins.garmin import GARMIN_SERVICE_UUID_GFDI
        result = self._parse(service_uuids=[GARMIN_SERVICE_UUID_GFDI])
        assert result is not None
        assert result.metadata["has_garmin_service_uuid"] is True
