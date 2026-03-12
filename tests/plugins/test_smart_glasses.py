"""Tests for Smart Glasses BLE advertisement plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser


COMPANY_IDS = {
    "meta_platforms": 0x01AB,
    "meta_technologies": 0x058E,
    "luxottica": 0x0D53,
    "snapchat": 0x03C2,
}

MANUFACTURER_NAMES = {
    0x01AB: "Meta Platforms",
    0x058E: "Meta Platforms Technologies",
    0x0D53: "Luxottica",
    0x03C2: "Snapchat",
}


def _make_mfr_data(company_id, payload=b"\x01\x02\x03\x04"):
    """Build manufacturer_data with little-endian company_id prefix."""
    return company_id.to_bytes(2, "little") + payload


def make_raw(manufacturer_data=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-06T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        service_data=None,
        service_uuids=[],
    )
    defaults.update(kwargs)
    return RawAdvertisement(manufacturer_data=manufacturer_data, **defaults)


@pytest.fixture
def parser():
    from adwatch.plugins.smart_glasses import SmartGlassesParser
    return SmartGlassesParser()


class TestSmartGlassesRegistration:
    def test_registers_with_all_company_ids(self):
        registry = ParserRegistry()

        from adwatch.plugins.smart_glasses import SmartGlassesParser

        @register_parser(
            name="smart_glasses",
            company_id=[0x01AB, 0x058E, 0x0D53, 0x03C2],
            description="Smart glasses BLE advertisements",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class TestGlasses(SmartGlassesParser):
            pass

        for cid_name, cid in COMPANY_IDS.items():
            ad = make_raw(manufacturer_data=_make_mfr_data(cid))
            matches = registry.match(ad)
            assert len(matches) == 1, f"Should match {cid_name} (0x{cid:04X})"

    def test_does_not_match_unrelated_company_id(self):
        registry = ParserRegistry()

        from adwatch.plugins.smart_glasses import SmartGlassesParser

        @register_parser(
            name="smart_glasses",
            company_id=[0x01AB, 0x058E, 0x0D53, 0x03C2],
            description="Smart glasses BLE advertisements",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class TestGlasses(SmartGlassesParser):
            pass

        ad = make_raw(manufacturer_data=_make_mfr_data(0x004C))  # Apple
        matches = registry.match(ad)
        assert len(matches) == 0


class TestSmartGlassesParsing:
    @pytest.mark.parametrize("cid_name,cid", list(COMPANY_IDS.items()))
    def test_parse_returns_result_for_each_company(self, parser, cid_name, cid):
        raw = make_raw(manufacturer_data=_make_mfr_data(cid))
        result = parser.parse(raw)
        assert result is not None
        assert isinstance(result, ParseResult)

    def test_parser_name(self, parser):
        raw = make_raw(manufacturer_data=_make_mfr_data(0x01AB))
        result = parser.parse(raw)
        assert result.parser_name == "smart_glasses"

    def test_beacon_type(self, parser):
        raw = make_raw(manufacturer_data=_make_mfr_data(0x01AB))
        result = parser.parse(raw)
        assert result.beacon_type == "smart_glasses"

    def test_device_class(self, parser):
        raw = make_raw(manufacturer_data=_make_mfr_data(0x01AB))
        result = parser.parse(raw)
        assert result.device_class == "wearable"

    def test_identity_hash_format(self, parser):
        raw = make_raw(manufacturer_data=_make_mfr_data(0x01AB))
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)  # must be valid hex

    def test_identity_hash_value(self, parser):
        payload = b"\x01\x02\x03\x04"
        raw = make_raw(
            manufacturer_data=_make_mfr_data(0x01AB, payload),
            mac_address="11:22:33:44:55:66",
        )
        result = parser.parse(raw)
        expected = hashlib.sha256(
            f"11:22:33:44:55:66:{_make_mfr_data(0x01AB, payload)[2:].hex()}".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_raw_payload_hex(self, parser):
        payload = b"\xAA\xBB\xCC"
        raw = make_raw(manufacturer_data=_make_mfr_data(0x058E, payload))
        result = parser.parse(raw)
        assert result.raw_payload_hex == payload.hex()

    @pytest.mark.parametrize("cid_name,cid", list(COMPANY_IDS.items()))
    def test_metadata_manufacturer(self, parser, cid_name, cid):
        raw = make_raw(manufacturer_data=_make_mfr_data(cid))
        result = parser.parse(raw)
        assert result.metadata["manufacturer"] == MANUFACTURER_NAMES[cid]

    def test_metadata_company_id_hex(self, parser):
        raw = make_raw(manufacturer_data=_make_mfr_data(0x03C2))
        result = parser.parse(raw)
        assert result.metadata["company_id"] == "0x03c2"


class TestSmartGlassesMalformed:
    def test_returns_none_no_manufacturer_data(self, parser):
        raw = make_raw(manufacturer_data=None)
        assert parser.parse(raw) is None

    def test_returns_none_too_short(self, parser):
        raw = make_raw(manufacturer_data=b"\xAB")
        assert parser.parse(raw) is None

    def test_returns_none_wrong_company_id(self, parser):
        raw = make_raw(manufacturer_data=_make_mfr_data(0x004C))
        assert parser.parse(raw) is None

    def test_returns_none_company_id_only_no_payload(self, parser):
        raw = make_raw(manufacturer_data=0x01AB.to_bytes(2, "little"))
        assert parser.parse(raw) is None


class TestSmartGlassesUI:
    def test_has_ui_config(self, parser):
        cfg = parser.ui_config()
        assert cfg is not None
        assert cfg.tab_name == "Smart Glasses"

    def test_has_info_banner(self, parser):
        cfg = parser.ui_config()
        banner = cfg.widgets[0]
        assert banner.widget_type == "info_banner"
        assert "company IDs" in banner.config["text"]

    def test_has_data_table(self, parser):
        cfg = parser.ui_config()
        table = cfg.widgets[1]
        assert table.widget_type == "data_table"

    def test_no_storage_schema(self, parser):
        assert parser.storage_schema() is None
