"""Tests for Audio-Technica plugin."""

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.audio_technica import (
    AudioTechnicaParser, AT_AIROHA_UUID, GAIA_BLE_UUID,
)


def _make_ad(**kw):
    defaults = {"timestamp": "2025-01-01T00:00:00Z", "mac_address": "AA:BB:CC:DD:EE:FF",
                "address_type": "random", "manufacturer_data": None, "service_data": None}
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(name="audio_technica", service_uuid=AT_AIROHA_UUID,
                     local_name_pattern=r"^ATH-", description="AT", version="1.0.0",
                     core=False, registry=registry)
    class _P(AudioTechnicaParser):
        pass
    return _P


class TestAudioTechnica:
    def test_match_airoha_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[AT_AIROHA_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_ath_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="ATH-M50xBT2")
        assert len(registry.match(ad)) == 1

    def test_airoha_chipset_tagged(self):
        result = AudioTechnicaParser().parse(_make_ad(service_uuids=[AT_AIROHA_UUID]))
        assert result.metadata["chipset_family"] == "airoha"

    def test_qualcomm_chipset_with_name(self):
        result = AudioTechnicaParser().parse(_make_ad(
            service_uuids=[GAIA_BLE_UUID], local_name="ATH-CKS50TW",
        ))
        assert result.metadata["chipset_family"] == "qualcomm_qcc"

    def test_returns_none_unrelated(self):
        assert AudioTechnicaParser().parse(_make_ad(local_name="Other")) is None

    def test_parse_basics(self):
        result = AudioTechnicaParser().parse(_make_ad(local_name="ATH-M50xBT"))
        assert result.parser_name == "audio_technica"
        assert result.device_class == "audio"
