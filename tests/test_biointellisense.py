"""Tests for the BioIntelliSense BioButton / BioSticker plugin.

Byte layout per apk-ble-hunting/reports/biointellisense-biomobileplus-android_passive.md.
The report's indices are into the AD payload *including* the 2-byte company ID,
so `manufacturer_payload` index N corresponds to report index N+2:

    report[2] = payload[0] -> environment (0x02 = staging, else production)
    report[3] = payload[1] -> bit7 busy/OTA-mutex, bits0-6 activation state
"""

import hashlib
import struct

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.biointellisense import (
    BioIntelliSenseParser,
    BIOINTELLISENSE_COMPANY_ID,
    BIO_SERVICE_UUID_PRIMARY,
    BIO_SERVICE_UUID_FALLBACK,
    BIO_SERVICE_UUIDS,
    ACTIVATION_STATES,
    ENVIRONMENTS,
    decode_activation_state,
)


def _make_ad(**kwargs):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "random",
        "manufacturer_data": None,
        "service_data": None,
        "service_uuids": [BIO_SERVICE_UUID_PRIMARY],
        "local_name": "BioButton",
    }
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _mfr(env=0x03, state_byte=0x01,
         company_id=BIOINTELLISENSE_COMPANY_ID) -> bytes:
    return struct.pack("<H", company_id) + bytes([env, state_byte])


class TestBioConstants:
    def test_service_uuids(self):
        assert BIO_SERVICE_UUID_PRIMARY == "278b67fe-266b-406c-bd40-25379402b58d"
        assert BIO_SERVICE_UUID_FALLBACK == "c75c7440-6c17-4c53-886e-8cc5655798ba"
        assert set(BIO_SERVICE_UUIDS) == {
            BIO_SERVICE_UUID_PRIMARY, BIO_SERVICE_UUID_FALLBACK
        }

    def test_company_id(self):
        assert BIOINTELLISENSE_COMPANY_ID == 0x08FD

    def test_activation_state_table(self):
        assert ACTIVATION_STATES[0] == "NOT_ACTIVATED"
        assert ACTIVATION_STATES[1] == "ACTIVATED_AND_SHOULD_BE_SYNCED"
        assert ACTIVATION_STATES[2] == "ACTIVATED_AND_SYNCED_RECENTLY"
        assert ACTIVATION_STATES[4] == "READY_TO_REPROVISION"

    def test_environments(self):
        assert ENVIRONMENTS[2] == "STAGING"
        assert ENVIRONMENTS[3] == "PRODUCTION"

    def test_reserved_activation_states(self):
        assert decode_activation_state(3) == "RESERVED"
        assert decode_activation_state(5) == "RESERVED"
        assert decode_activation_state(0x7F) == "RESERVED"
        assert decode_activation_state(4) == "READY_TO_REPROVISION"


class TestBioMatching:
    def _register(self, registry):
        @register_parser(
            name="biointellisense",
            company_id=BIOINTELLISENSE_COMPANY_ID,
            service_uuid=list(BIO_SERVICE_UUIDS),
            local_name_pattern=r"(?i)^bio(button|sticker)",
            description="BioIntelliSense",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class _P(BioIntelliSenseParser):
            pass

        return _P

    def test_match_primary_uuid(self):
        registry = ParserRegistry()
        self._register(registry)
        ad = _make_ad(local_name=None, service_uuids=[BIO_SERVICE_UUID_PRIMARY.upper()])
        assert len(registry.match(ad)) == 1

    def test_match_fallback_uuid(self):
        registry = ParserRegistry()
        self._register(registry)
        ad = _make_ad(local_name=None, service_uuids=[BIO_SERVICE_UUID_FALLBACK])
        assert len(registry.match(ad)) == 1

    def test_match_name(self):
        registry = ParserRegistry()
        self._register(registry)
        assert len(registry.match(_make_ad(service_uuids=[], local_name="BioSticker"))) == 1

    def test_no_match_unrelated(self):
        registry = ParserRegistry()
        self._register(registry)
        ad = _make_ad(service_uuids=["180d"], local_name="Polar H10",
                      manufacturer_data=_mfr(company_id=0x006B))
        assert registry.match(ad) == []


class TestBioParse:
    def test_production_activated_should_sync(self):
        result = BioIntelliSenseParser().parse(
            _make_ad(manufacturer_data=_mfr(env=0x03, state_byte=0x01))
        )
        assert result is not None
        assert result.device_class == "medical"
        assert result.metadata["environment"] == "PRODUCTION"
        assert result.metadata["activation_state"] == "ACTIVATED_AND_SHOULD_BE_SYNCED"
        assert result.metadata["activation_state_value"] == 1
        assert result.metadata["busy"] is False

    def test_staging_environment(self):
        result = BioIntelliSenseParser().parse(
            _make_ad(manufacturer_data=_mfr(env=0x02, state_byte=0x00))
        )
        assert result.metadata["environment"] == "STAGING"
        assert result.metadata["activation_state"] == "NOT_ACTIVATED"

    def test_busy_bit_set(self):
        result = BioIntelliSenseParser().parse(
            _make_ad(manufacturer_data=_mfr(state_byte=0x82))
        )
        assert result.metadata["busy"] is True
        assert result.metadata["activation_state_value"] == 2
        assert result.metadata["activation_state"] == "ACTIVATED_AND_SYNCED_RECENTLY"

    def test_ready_to_reprovision(self):
        result = BioIntelliSenseParser().parse(
            _make_ad(manufacturer_data=_mfr(state_byte=0x04))
        )
        assert result.metadata["activation_state"] == "READY_TO_REPROVISION"

    def test_reserved_state(self):
        result = BioIntelliSenseParser().parse(
            _make_ad(manufacturer_data=_mfr(state_byte=0x03))
        )
        assert result.metadata["activation_state"] == "RESERVED"

    def test_unknown_environment_byte_is_production(self):
        result = BioIntelliSenseParser().parse(
            _make_ad(manufacturer_data=_mfr(env=0x77))
        )
        assert result.metadata["environment"] == "PRODUCTION"
        assert result.metadata["environment_byte"] == 0x77

    def test_env_only_payload_no_state(self):
        ad = _make_ad(manufacturer_data=struct.pack("<H", BIOINTELLISENSE_COMPANY_ID) + b"\x02")
        result = BioIntelliSenseParser().parse(ad)
        assert result.metadata["environment"] == "STAGING"
        assert "activation_state" not in result.metadata

    def test_no_mfr_data_presence_only(self):
        result = BioIntelliSenseParser().parse(_make_ad(manufacturer_data=None))
        assert result is not None
        assert result.metadata["device_name"] == "BioButton"
        assert "environment" not in result.metadata

    def test_fallback_uuid_recorded(self):
        result = BioIntelliSenseParser().parse(
            _make_ad(service_uuids=[BIO_SERVICE_UUID_FALLBACK])
        )
        assert result.metadata["service_uuid"] == BIO_SERVICE_UUID_FALLBACK

    def test_identity_hash_mac_based(self):
        result = BioIntelliSenseParser().parse(_make_ad())
        expected = hashlib.sha256(b"biointellisense:AA:BB:CC:DD:EE:FF").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_unrelated_returns_none(self):
        assert BioIntelliSenseParser().parse(
            _make_ad(service_uuids=["fd6f"], local_name="Contact Tracer")
        ) is None

    def test_company_id_mismatch_still_decodes(self):
        # The app never validates the company ID — a UUID match is enough.
        result = BioIntelliSenseParser().parse(
            _make_ad(manufacturer_data=_mfr(env=0x02, state_byte=0x04,
                                            company_id=0x1234))
        )
        assert result.metadata["environment"] == "STAGING"
        assert result.metadata["activation_state"] == "READY_TO_REPROVISION"
