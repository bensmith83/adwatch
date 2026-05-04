"""Tests for Sonos speaker plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult


@pytest.fixture
def parser():
    from adwatch.plugins.sonos import SonosParser
    return SonosParser()


def make_raw(manufacturer_data=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-05T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        service_data=None,
        service_uuids=[],
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        manufacturer_data=manufacturer_data,
        **defaults,
    )


SONOS_COMPANY_ID = 0x05A7
# Company ID in little-endian bytes + 16 bytes of sample payload
SONOS_COMPANY_BYTES = SONOS_COMPANY_ID.to_bytes(2, "little")  # b'\xa7\x05'
SONOS_PAYLOAD = bytes(range(0x10, 0x20))  # 16 bytes of sample payload
SONOS_MANUFACTURER_DATA = SONOS_COMPANY_BYTES + SONOS_PAYLOAD


class TestSonosParsing:
    def test_parse_valid_sonos(self, parser):
        raw = make_raw(manufacturer_data=SONOS_MANUFACTURER_DATA)
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(manufacturer_data=SONOS_MANUFACTURER_DATA)
        result = parser.parse(raw)
        assert result.parser_name == "sonos"

    def test_beacon_type(self, parser):
        raw = make_raw(manufacturer_data=SONOS_MANUFACTURER_DATA)
        result = parser.parse(raw)
        assert result.beacon_type == "sonos"

    def test_device_class_speaker(self, parser):
        raw = make_raw(manufacturer_data=SONOS_MANUFACTURER_DATA)
        result = parser.parse(raw)
        assert result.device_class == "speaker"

    def test_identity_hash(self, parser):
        """Identity = SHA256(mac_address)[:16]."""
        raw = make_raw(
            manufacturer_data=SONOS_MANUFACTURER_DATA,
            mac_address="AA:BB:CC:DD:EE:FF",
        )
        result = parser.parse(raw)
        expected = hashlib.sha256("AA:BB:CC:DD:EE:FF".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_hash_format(self, parser):
        raw = make_raw(manufacturer_data=SONOS_MANUFACTURER_DATA)
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)  # must be valid hex

    def test_raw_payload_hex(self, parser):
        raw = make_raw(manufacturer_data=SONOS_MANUFACTURER_DATA)
        result = parser.parse(raw)
        assert result.raw_payload_hex == SONOS_PAYLOAD.hex()

    def test_metadata_payload_hex(self, parser):
        raw = make_raw(manufacturer_data=SONOS_MANUFACTURER_DATA)
        result = parser.parse(raw)
        assert result.metadata["payload_hex"] == SONOS_PAYLOAD.hex()

    def test_metadata_payload_length(self, parser):
        raw = make_raw(manufacturer_data=SONOS_MANUFACTURER_DATA)
        result = parser.parse(raw)
        assert result.metadata["payload_length"] == len(SONOS_PAYLOAD)

    def test_large_payload(self, parser):
        """150-byte manufacturer_data (2 company ID + 148 payload)."""
        mfr_data = SONOS_COMPANY_BYTES + bytes(148)
        raw = make_raw(manufacturer_data=mfr_data)
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["payload_length"] == 148

    def test_no_storage(self, parser):
        assert parser.storage_schema() is None

    def test_has_ui(self, parser):
        cfg = parser.ui_config()
        assert cfg is not None
        assert cfg.tab_name == "Sonos"
        assert cfg.tab_icon == "speaker"

    def test_ui_widget(self, parser):
        cfg = parser.ui_config()
        assert len(cfg.widgets) == 1
        assert cfg.widgets[0].widget_type == "data_table"

    def test_ui_render_hints(self, parser):
        cfg = parser.ui_config()
        hints = cfg.widgets[0].render_hints
        assert hints is not None
        assert hints["columns"] == ["timestamp", "mac_address", "local_name", "payload_length", "rssi_max", "sighting_count"]


class TestSonosMalformed:
    def test_returns_none_no_manufacturer_data(self, parser):
        raw = make_raw(manufacturer_data=None)
        assert parser.parse(raw) is None

    def test_returns_none_wrong_company_id(self, parser):
        # Apple company ID instead of Sonos
        wrong_mfr = (0x004C).to_bytes(2, "little") + SONOS_PAYLOAD
        raw = make_raw(manufacturer_data=wrong_mfr)
        assert parser.parse(raw) is None

    def test_returns_none_too_short(self, parser):
        """Only company ID bytes, no payload."""
        raw = make_raw(manufacturer_data=SONOS_COMPANY_BYTES)
        assert parser.parse(raw) is None

    def test_different_mac_different_identity(self, parser):
        raw1 = make_raw(
            manufacturer_data=SONOS_MANUFACTURER_DATA,
            mac_address="11:22:33:44:55:66",
        )
        raw2 = make_raw(
            manufacturer_data=SONOS_MANUFACTURER_DATA,
            mac_address="AA:BB:CC:DD:EE:FF",
        )
        r1 = parser.parse(raw1)
        r2 = parser.parse(raw2)
        assert r1.identifier_hash != r2.identifier_hash


class TestSonosEnrichedMatching:
    """v1.1.0: service UUID 0xFE07 + ^Sonos name pattern."""

    def test_match_service_uuid_short(self, parser):
        raw = make_raw(service_uuids=["fe07"])
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata.get("match_source") == "service_uuid"

    def test_match_service_uuid_full(self, parser):
        raw = make_raw(service_uuids=["0000fe07-0000-1000-8000-00805f9b34fb"])
        result = parser.parse(raw)
        assert result is not None

    def test_match_sonos_name_prefix(self, parser):
        raw = make_raw(local_name="Sonos Era 100")
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["device_name"] == "Sonos Era 100"

    def test_uuid_match_no_payload_still_works(self, parser):
        raw = make_raw(service_uuids=["fe07"], manufacturer_data=None)
        result = parser.parse(raw)
        assert result is not None
