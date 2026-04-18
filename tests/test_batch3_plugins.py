"""Tests for batch 3 plugins: kwikset, schlage, ecobee."""

import hashlib
import struct

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


# ---- Kwikset ---------------------------------------------------------------

def _kwikset_consumer_mfr(unique_id=bytes(range(9)), product_id=0x01, ble_status=0x00,
                         proto=1, pair=0x00, gen=0x00, ac=0x00):
    # Layout (consumer variant): [unique_id(9)] [company_id(2)=0x0356 LE] [prod] [blst] [prot] [pair] [gen] [ac]
    return unique_id + bytes([0x56, 0x03]) + bytes([product_id, ble_status, proto, pair, gen, ac])


def _kwikset_halo3_mfr(unique_id=bytes(range(9)), product_id=0x05):
    # Halo3: [unique_id(9)] [0x0356] [prod] [blst] [prot=3] [pair] [gen] [ac] [pan] [res(2)] [lock_status]
    return unique_id + bytes([0x56, 0x03]) + bytes([product_id, 0x00, 3, 0x00, 0x00, 0x00, 0x42, 0x00, 0x00, 0x07])


class TestKwikset:
    @pytest.fixture
    def parser(self):
        from adwatch.plugins.kwikset import KwiksetParser
        return KwiksetParser()

    def test_detects_consumer_variant(self, parser):
        ad = _make_ad(manufacturer_data=_kwikset_consumer_mfr(proto=2))
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["variant"] == "consumer"
        assert result.metadata["protocol_version"] == 2

    def test_detects_halo3_variant(self, parser):
        ad = _make_ad(manufacturer_data=_kwikset_halo3_mfr())
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["variant"] == "halo3"
        assert result.metadata["protocol_version"] == 3
        assert result.metadata["lock_status_info"] == 0x07
        assert result.metadata["pan_discriminator"] == 0x42

    def test_unique_id_extracted(self, parser):
        uid = bytes(range(0x10, 0x19))
        ad = _make_ad(manufacturer_data=_kwikset_consumer_mfr(unique_id=uid))
        result = parser.parse(ad)
        assert result.metadata["unique_id_hex"] == uid.hex()

    def test_service_uuid_fallback(self, parser):
        from adwatch.plugins.kwikset import LOCK_SYSTEM_UUID
        ad = _make_ad(service_uuids=[LOCK_SYSTEM_UUID])
        result = parser.parse(ad)
        assert result is not None

    def test_rejects_non_kwikset(self, parser):
        ad = _make_ad(manufacturer_data=bytes([0x4C, 0x00]) + bytes(14))
        assert parser.parse(ad) is None


# ---- Schlage ---------------------------------------------------------------

class TestSchlage:
    @pytest.fixture
    def parser(self):
        from adwatch.plugins.schlage import SchlageParser
        return SchlageParser()

    def test_sense_name(self, parser):
        ad = _make_ad(local_name="SENSE_ABC123")
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["product"] == "Sense"

    def test_encode_name_extracts_serial(self, parser):
        ad = _make_ad(local_name="schlage12345678")
        result = parser.parse(ad)
        assert result.metadata["product"] == "Encode"
        assert result.metadata["serial"] == "12345678"

    def test_nde_name(self, parser):
        ad = _make_ad(local_name="NDE-001")
        assert parser.parse(ad).metadata["product"] == "NDE 358"

    def test_uweave_uuid_match(self, parser):
        from adwatch.plugins.schlage import SENSE_UWEAVE_UUID
        ad = _make_ad(service_uuids=[SENSE_UWEAVE_UUID])
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["has_uweave_service"] is True

    def test_no_match(self, parser):
        assert parser.parse(_make_ad(local_name="Random")) is None

    @pytest.mark.parametrize("name", [
        "Smart Sense Thermostat",   # contains "sense" as substring
        "Defense Monitor",          # contains "nse" but not as prefix
        "Pretend-NDE Beacon",       # contains "NDE" mid-string
    ])
    def test_rejects_unanchored_substring_match(self, parser, name):
        assert parser.parse(_make_ad(local_name=name)) is None


# ---- ecobee ----------------------------------------------------------------

class TestEcobee:
    @pytest.fixture
    def parser(self):
        from adwatch.plugins.ecobee import EcobeeParser
        return EcobeeParser()

    def test_thermostat_serial_family(self, parser):
        ad = _make_ad(local_name="ecobee Inc. - 611234567")
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["serial"] == "611234567"
        assert "thermostat" in result.metadata["product_family"]

    def test_camera_serial_family(self, parser):
        ad = _make_ad(local_name="ecobee Inc. - 711234567")
        result = parser.parse(ad)
        assert result.metadata["product_family"] == "camera (THEIA)"

    def test_contact_sensor_family(self, parser):
        ad = _make_ad(local_name="ecobee Inc. - 721234567")
        result = parser.parse(ad)
        assert result.metadata["product_family"] == "contact sensor (HECATE)"

    def test_identity_hash_by_serial(self, parser):
        ad = _make_ad(local_name="ecobee Inc. - 611234567")
        result = parser.parse(ad)
        expected = hashlib.sha256("ecobee:611234567".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_no_match_wrong_prefix(self, parser):
        assert parser.parse(_make_ad(local_name="Not ecobee")) is None

    def test_no_match_short_serial(self, parser):
        assert parser.parse(_make_ad(local_name="ecobee Inc. - 12345")) is None
