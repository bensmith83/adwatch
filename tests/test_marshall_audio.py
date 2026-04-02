"""Tests for Marshall Bluetooth speaker BLE advertisement plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.marshall_audio import MarshallAudioParser, MARSHALL_SERVICE_UUID


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
        name="marshall_audio",
        service_uuid=MARSHALL_SERVICE_UUID,
        description="Marshall Bluetooth speaker advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(MarshallAudioParser):
        pass

    return registry


class TestMarshallAudioRegistry:
    def test_matches_service_uuid(self):
        """Matches when service_uuids contains the Marshall UUID."""
        registry = _make_registry()
        ad = _make_ad(service_uuids=["fe8f"])
        matches = registry.match(ad)
        assert len(matches) >= 1

    def test_no_match_unrelated(self):
        """Returns empty for unrelated advertisement."""
        registry = _make_registry()
        ad = _make_ad(local_name="SomeOtherDevice")
        matches = registry.match(ad)
        assert len(matches) == 0


class TestMarshallAudioParser:
    def test_parser_name(self):
        """parser_name is 'marshall_audio'."""
        parser = MarshallAudioParser()
        ad = _make_ad(
            service_uuids=["fe8f"],
            local_name="STANMORE II",
        )
        result = parser.parse(ad)
        assert result.parser_name == "marshall_audio"

    def test_beacon_type(self):
        """beacon_type is 'marshall_audio'."""
        parser = MarshallAudioParser()
        ad = _make_ad(
            service_uuids=["fe8f"],
            local_name="STANMORE II",
        )
        result = parser.parse(ad)
        assert result.beacon_type == "marshall_audio"

    def test_device_class(self):
        """device_class is 'speaker'."""
        parser = MarshallAudioParser()
        ad = _make_ad(
            service_uuids=["fe8f"],
            local_name="STANMORE II",
        )
        result = parser.parse(ad)
        assert result.device_class == "speaker"

    def test_model_from_known_name(self):
        """Known Marshall name populates model metadata."""
        parser = MarshallAudioParser()
        ad = _make_ad(
            service_uuids=["fe8f"],
            local_name="STANMORE II",
        )
        result = parser.parse(ad)
        assert result.metadata["model"] == "STANMORE II"

    def test_qualcomm_company_id_match(self):
        """Parses with UUID + Qualcomm company_id 0x0912 even without known name."""
        parser = MarshallAudioParser()
        mfr_data = (0x0912).to_bytes(2, "little") + b"\x01\x02\x03"
        ad = _make_ad(
            service_uuids=["fe8f"],
            manufacturer_data=mfr_data,
        )
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "marshall_audio"

    def test_identity_hash(self):
        """Identity hash is SHA256(mac_address:marshall_audio)[:16]."""
        mac = "11:22:33:44:55:66"
        parser = MarshallAudioParser()
        ad = _make_ad(
            mac_address=mac,
            service_uuids=["fe8f"],
            local_name="STANMORE II",
        )
        result = parser.parse(ad)
        expected = hashlib.sha256(f"{mac}:marshall_audio".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_returns_none_unknown_name_uuid_only(self):
        """Returns None for UUID match with unknown name and no Qualcomm company_id."""
        parser = MarshallAudioParser()
        ad = _make_ad(
            service_uuids=["fe8f"],
            local_name="UnknownSpeaker",
        )
        result = parser.parse(ad)
        assert result is None

    def test_returns_none_no_uuid(self):
        """Returns None when UUID is not present."""
        parser = MarshallAudioParser()
        ad = _make_ad(local_name="STANMORE II")
        result = parser.parse(ad)
        assert result is None
