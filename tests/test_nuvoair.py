"""Tests for the NuvoAir AirNext spirometer plugin.

Byte layouts per apk-ble-hunting/reports/nuvoair-aria_passive.md.
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.nuvoair import (
    NuvoAirParser,
    NUVOAIR_AOS_SERVICE_UUID,
    NUVOAIR_NEW_SERVICE_UUID,
    NORDIC_LEGACY_DFU_UUID,
    NORDIC_COMPANY_ID,
)


def _make_ad(**kw):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "C0:1A:2B:3C:4D:5E",
        "address_type": "public",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(
        name="nuvoair",
        service_uuid=[NUVOAIR_AOS_SERVICE_UUID, NUVOAIR_NEW_SERVICE_UUID],
        local_name_pattern=r"^AIR-DFU$",
        description="NuvoAir",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(NuvoAirParser):
        pass

    return _P


class TestNuvoAirMatching:
    def test_matches_aos_service_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[NUVOAIR_AOS_SERVICE_UUID])
        assert len(registry.match(ad)) == 1

    def test_matches_short_aos_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=["abcd"])
        assert len(registry.match(ad)) == 1

    def test_matches_new_service_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[NUVOAIR_NEW_SERVICE_UUID])
        assert len(registry.match(ad)) == 1

    def test_matches_air_dfu_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="AIR-DFU")
        assert len(registry.match(ad)) == 1

    def test_matches_service_data_key(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_data={"abcd": bytes([1, 32, 0, 0])})
        assert len(registry.match(ad)) == 1

    def test_bare_dfutarg_name_not_registered(self):
        """Generic Nordic bootloader name must not claim every DFU device."""
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="DfuTarg")
        assert registry.match(ad) == []


class TestNuvoAirAosServiceData:
    def test_decodes_four_byte_service_data(self):
        # fw 1.32, 7 stored sessions, rtcNotSet clear
        ad = _make_ad(
            service_uuids=[NUVOAIR_AOS_SERVICE_UUID],
            service_data={"abcd": bytes([0x01, 0x20, 0x07, 0x00])},
        )
        result = NuvoAirParser().parse(ad)
        assert result is not None
        assert result.metadata["firmware_major"] == 1
        assert result.metadata["firmware_minor"] == 32
        assert result.metadata["firmware_version"] == "1.32"
        assert result.metadata["num_sessions"] == 7
        assert result.metadata["has_advertised_sessions"] is True
        assert result.metadata["rtc_not_set"] is False
        assert result.metadata["generation"] == "aos"

    def test_rtc_not_set_flag(self):
        ad = _make_ad(
            service_data={"abcd": bytes([0x01, 0x05, 0x00, 0x01])},
        )
        result = NuvoAirParser().parse(ad)
        assert result.metadata["rtc_not_set"] is True
        assert result.metadata["spacer_flag"] is False
        assert result.metadata["num_sessions"] == 0
        assert result.metadata["has_advertised_sessions"] is False

    def test_spacer_flag_bit1(self):
        ad = _make_ad(service_data={"abcd": bytes([0x02, 0x00, 0x03, 0x02])})
        result = NuvoAirParser().parse(ad)
        assert result.metadata["spacer_flag"] is True
        assert result.metadata["rtc_not_set"] is False

    def test_firmware_minor_zero_padded(self):
        ad = _make_ad(service_data={"abcd": bytes([0x02, 0x03, 0x00, 0x00])})
        result = NuvoAirParser().parse(ad)
        assert result.metadata["firmware_version"] == "2.03"

    def test_required_version_flag(self):
        ad = _make_ad(service_data={"abcd": bytes([0x01, 0x20, 0x00, 0x00])})
        assert NuvoAirParser().parse(ad).metadata["is_required_version"] is True
        ad2 = _make_ad(service_data={"abcd": bytes([0x01, 0x1F, 0x00, 0x00])})
        assert NuvoAirParser().parse(ad2).metadata["is_required_version"] is False

    def test_service_data_wrong_length_not_decoded(self):
        ad = _make_ad(service_data={"abcd": bytes([0x01, 0x20, 0x07])})
        result = NuvoAirParser().parse(ad)
        assert result is not None
        assert "firmware_major" not in result.metadata

    def test_full_uuid_service_data_key(self):
        ad = _make_ad(
            service_data={NUVOAIR_AOS_SERVICE_UUID: bytes([0x01, 0x20, 0x02, 0x00])}
        )
        result = NuvoAirParser().parse(ad)
        assert result.metadata["num_sessions"] == 2

    def test_dfu_base_uuid_service_data(self):
        """AOS devices may publish the same blob under the 0x1530 SIG-base UUID."""
        ad = _make_ad(service_data={"1530": bytes([0x01, 0x20, 0x04, 0x00])})
        result = NuvoAirParser().parse(ad)
        assert result is not None
        assert result.metadata["num_sessions"] == 4


class TestNuvoAirManufacturerFallback:
    def test_nordic_fallback_session_count(self):
        ad = _make_ad(
            service_uuids=[NUVOAIR_AOS_SERVICE_UUID],
            manufacturer_data=bytes([0x59, 0x00, 0x0C]),
        )
        result = NuvoAirParser().parse(ad)
        assert result.metadata["num_sessions"] == 12
        assert result.metadata["num_sessions_source"] == "manufacturer_data"
        assert result.metadata["has_advertised_sessions"] is True

    def test_service_data_wins_over_manufacturer_fallback(self):
        ad = _make_ad(
            service_data={"abcd": bytes([0x01, 0x20, 0x05, 0x00])},
            manufacturer_data=bytes([0x59, 0x00, 0x63]),
        )
        result = NuvoAirParser().parse(ad)
        assert result.metadata["num_sessions"] == 5
        assert result.metadata["num_sessions_source"] == "service_data"

    def test_nordic_cid_alone_does_not_match(self):
        """0x0059 is Nordic's generic CID — never a NuvoAir signal on its own."""
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=bytes([0x59, 0x00, 0x0C]))
        assert registry.match(ad) == []
        assert NuvoAirParser().parse(ad) is None

    def test_non_nordic_manufacturer_data_ignored(self):
        ad = _make_ad(
            service_uuids=[NUVOAIR_AOS_SERVICE_UUID],
            manufacturer_data=bytes([0x4C, 0x00, 0x0C]),
        )
        result = NuvoAirParser().parse(ad)
        assert "num_sessions" not in result.metadata


class TestNuvoAirDfuMode:
    def test_air_dfu_name_sets_dfu_mode(self):
        ad = _make_ad(local_name="AIR-DFU")
        result = NuvoAirParser().parse(ad)
        assert result is not None
        assert result.metadata["dfu_mode"] is True
        assert result.metadata["generation"] == "airnext"

    def test_dfutarg_with_nordic_dfu_uuid(self):
        ad = _make_ad(
            local_name="DfuTarg", service_uuids=[NORDIC_LEGACY_DFU_UUID]
        )
        result = NuvoAirParser().parse(ad)
        assert result is not None
        assert result.metadata["dfu_mode"] is True
        assert result.metadata["generation"] == "aos"

    def test_dfutarg_alone_returns_none(self):
        ad = _make_ad(local_name="DfuTarg")
        assert NuvoAirParser().parse(ad) is None


class TestNuvoAirIdentityAndBasics:
    def test_identity_hash_from_mac(self):
        ad = _make_ad(service_uuids=[NUVOAIR_AOS_SERVICE_UUID])
        result = NuvoAirParser().parse(ad)
        expected = hashlib.sha256(
            f"nuvoair:{ad.mac_address}".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_stable_across_session_count_change(self):
        a = _make_ad(service_data={"abcd": bytes([0x01, 0x20, 0x01, 0x00])})
        b = _make_ad(service_data={"abcd": bytes([0x01, 0x20, 0x09, 0x00])})
        assert NuvoAirParser().parse(a).identifier_hash == \
            NuvoAirParser().parse(b).identifier_hash

    def test_basics(self):
        ad = _make_ad(service_uuids=[NUVOAIR_NEW_SERVICE_UUID])
        result = NuvoAirParser().parse(ad)
        assert result.parser_name == "nuvoair"
        assert result.beacon_type == "nuvoair"
        assert result.device_class == "medical"
        assert result.metadata["vendor"] == "NuvoAir"
        assert result.metadata["product"] == "AirNext spirometer"

    def test_new_generation_uuid_marks_airnext(self):
        ad = _make_ad(service_uuids=[NUVOAIR_NEW_SERVICE_UUID])
        assert NuvoAirParser().parse(ad).metadata["generation"] == "airnext"

    def test_local_name_recorded(self):
        ad = _make_ad(service_uuids=["abcd"], local_name="AirNext")
        assert NuvoAirParser().parse(ad).metadata["device_name"] == "AirNext"

    def test_returns_none_for_unrelated(self):
        assert NuvoAirParser().parse(_make_ad(local_name="Whatever")) is None

    def test_nordic_company_id_constant(self):
        assert NORDIC_COMPANY_ID == 0x0059
