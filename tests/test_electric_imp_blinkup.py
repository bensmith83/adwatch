"""Tests for the Electric Imp BlinkUp BLE provisioning plugin.

Source: apk-ble-hunting/reports/tovala-tovala_passive.md — the Tovala smart
oven commissions over "bleblinkup", whose single advertised vendor service
UUID `FADA47BE-C455-48C9-A5F2-AF7CF368D719` is cited in the visible Java
tree (`rq/e.java:56`) and is the report's recommended scan filter.
"""

import hashlib

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.electric_imp_blinkup import (
    ElectricImpBlinkUpParser,
    BLINKUP_SERVICE_UUID,
)


def _make_ad(**kwargs):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "public",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _registry():
    registry = ParserRegistry()

    @register_parser(
        name="electric_imp_blinkup",
        service_uuid=BLINKUP_SERVICE_UUID,
        description="Electric Imp BlinkUp",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(ElectricImpBlinkUpParser):
        pass

    return registry


class TestBlinkUpConstants:
    def test_service_uuid(self):
        assert BLINKUP_SERVICE_UUID == "fada47be-c455-48c9-a5f2-af7cf368d719"


class TestBlinkUpMatching:
    def test_matches_service_uuid(self):
        ad = _make_ad(service_uuids=[BLINKUP_SERVICE_UUID])
        assert len(_registry().match(ad)) == 1

    def test_matches_uppercase_service_uuid(self):
        ad = _make_ad(service_uuids=[BLINKUP_SERVICE_UUID.upper()])
        assert len(_registry().match(ad)) == 1

    def test_matches_service_data_key(self):
        ad = _make_ad(service_data={BLINKUP_SERVICE_UUID: b"\x01\x02"})
        assert len(_registry().match(ad)) == 1

    def test_does_not_match_other_uuid(self):
        ad = _make_ad(service_uuids=["0000fff0-0000-1000-8000-00805f9b34fb"])
        assert _registry().match(ad) == []

    def test_parse_rejects_without_uuid(self):
        ad = _make_ad(local_name="imp_004a")
        assert ElectricImpBlinkUpParser().parse(ad) is None


class TestBlinkUpMetadata:
    def test_base_metadata(self):
        ad = _make_ad(service_uuids=[BLINKUP_SERVICE_UUID])
        result = ElectricImpBlinkUpParser().parse(ad)
        assert result is not None
        assert result.parser_name == "electric_imp_blinkup"
        assert result.beacon_type == "electric_imp_blinkup"
        assert result.device_class == "provisioning"
        assert result.metadata["ecosystem"] == "electric-imp-blinkup"
        assert result.metadata["provisioning_mode"] is True

    def test_device_name_recorded(self):
        ad = _make_ad(service_uuids=[BLINKUP_SERVICE_UUID], local_name="imp_004a")
        result = ElectricImpBlinkUpParser().parse(ad)
        assert result.metadata["device_name"] == "imp_004a"

    @pytest.mark.parametrize("name", ["imp_004a", "imp-OS", "IMP_ABC"])
    def test_default_imp_name_flagged(self, name):
        ad = _make_ad(service_uuids=[BLINKUP_SERVICE_UUID], local_name=name)
        result = ElectricImpBlinkUpParser().parse(ad)
        assert result.metadata["imp_default_name"] is True

    def test_non_imp_name_not_flagged(self):
        ad = _make_ad(service_uuids=[BLINKUP_SERVICE_UUID], local_name="Kitchen Oven")
        result = ElectricImpBlinkUpParser().parse(ad)
        assert "imp_default_name" not in result.metadata

    def test_tovala_product_hint(self):
        ad = _make_ad(service_uuids=[BLINKUP_SERVICE_UUID], local_name="Tovala Oven 12")
        result = ElectricImpBlinkUpParser().parse(ad)
        assert result.metadata["product_hint"] == "Tovala Smart Oven"

    def test_no_product_hint_by_default(self):
        """The UUID is cross-vendor -- do not claim Tovala without evidence."""
        ad = _make_ad(service_uuids=[BLINKUP_SERVICE_UUID])
        result = ElectricImpBlinkUpParser().parse(ad)
        assert "product_hint" not in result.metadata

    def test_service_data_hex_recorded(self):
        ad = _make_ad(service_data={BLINKUP_SERVICE_UUID: b"\xde\xad\xbe\xef"})
        result = ElectricImpBlinkUpParser().parse(ad)
        assert result.metadata["service_data_hex"] == "deadbeef"


class TestBlinkUpIdentity:
    def test_identity_hash_from_mac(self):
        ad = _make_ad(service_uuids=[BLINKUP_SERVICE_UUID],
                      mac_address="11:22:33:44:55:66")
        result = ElectricImpBlinkUpParser().parse(ad)
        expected = hashlib.sha256(
            b"electric_imp_blinkup:11:22:33:44:55:66").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_length(self):
        ad = _make_ad(service_uuids=[BLINKUP_SERVICE_UUID])
        result = ElectricImpBlinkUpParser().parse(ad)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)
