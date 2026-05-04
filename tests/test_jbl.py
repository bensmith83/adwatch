"""Tests for JBL speaker BLE advertisement plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.jbl import JblParser, JBL_SERVICE_UUID, JBL_NAME_RE, HARMAN_COMPANY_ID


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
        name="jbl",
        service_uuid=JBL_SERVICE_UUID,
        local_name_pattern=r"^JBL ",
        description="JBL speaker advertisements",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser(JblParser):
        pass

    return registry


class TestJblMatching:
    def test_matches_service_uuid(self):
        """Matches on JBL/Harman service UUID FDDF."""
        registry = _make_registry()
        ad = _make_ad(
            service_uuids=["0000fddf-0000-1000-8000-00805f9b34fb"],
            local_name="JBL PartyBox Stage 320",
        )
        matches = registry.match(ad)
        assert len(matches) == 1

    def test_matches_local_name(self):
        """Matches on JBL prefix."""
        registry = _make_registry()
        ad = _make_ad(local_name="JBL PartyBox Stage 320")
        matches = registry.match(ad)
        assert len(matches) == 1

    def test_no_match_unrelated(self):
        """Does not match unrelated devices."""
        parser = JblParser()
        ad = _make_ad(local_name="SomeDevice")
        result = parser.parse(ad)
        assert result is None


class TestJblParsing:
    def test_parse_basic(self):
        """Parses JBL speaker advertisement."""
        parser = JblParser()
        ad = _make_ad(
            local_name="JBL PartyBox Stage 320",
            service_uuids=["0000fddf-0000-1000-8000-00805f9b34fb"],
        )
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "jbl"
        assert result.beacon_type == "jbl"
        assert result.device_class == "speaker"

    def test_model_from_name(self):
        """Model extracted from local name (after 'JBL ')."""
        parser = JblParser()
        ad = _make_ad(
            local_name="JBL PartyBox Stage 320",
            service_uuids=["0000fddf-0000-1000-8000-00805f9b34fb"],
        )
        result = parser.parse(ad)
        assert result.metadata["model"] == "PartyBox Stage 320"

    def test_parse_with_harman_mfr_data(self):
        """Parses Harman manufacturer data."""
        parser = JblParser()
        mfr = bytes.fromhex("cb0edd2001d06486a92401000068593259334901010000000000")
        ad = _make_ad(
            local_name="JBL PartyBox Stage 320",
            manufacturer_data=mfr,
            service_data={"fddf": b""},
        )
        result = parser.parse(ad)
        assert result is not None
        assert result.raw_payload_hex == mfr.hex()

    def test_parse_with_fe2c_service_data(self):
        """Parses JBL with FE2C service data (FMDN/location)."""
        parser = JblParser()
        ad = _make_ad(
            local_name="JBL PartyBox Stage 320",
            service_data={
                "fddf": b"",
                "fe2c": bytes.fromhex("1060c531a6a6861c21aa8f"),
            },
        )
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata.get("has_fmdn") is True

    def test_identity_hash(self):
        """Identity hash is SHA256('jbl:{mac}')[:16]."""
        mac = "11:22:33:44:55:66"
        parser = JblParser()
        ad = _make_ad(
            local_name="JBL PartyBox Stage 320",
            service_uuids=["0000fddf-0000-1000-8000-00805f9b34fb"],
            mac_address=mac,
        )
        result = parser.parse(ad)
        expected = hashlib.sha256(f"jbl:{mac}".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_uuid_only_match(self):
        """Matches on FDDF UUID alone."""
        parser = JblParser()
        ad = _make_ad(
            service_uuids=["0000fddf-0000-1000-8000-00805f9b34fb"],
            service_data={"fddf": b""},
        )
        result = parser.parse(ad)
        assert result is not None

    def test_no_match_without_signals(self):
        """Returns None without matching name, UUID, or service data."""
        parser = JblParser()
        ad = _make_ad()
        result = parser.parse(ad)
        assert result is None

    def test_fddf_service_data_match(self):
        """Matches on FDDF service data key."""
        parser = JblParser()
        ad = _make_ad(
            service_data={"fddf": b""},
        )
        result = parser.parse(ad)
        assert result is not None


class TestJblPidAndBdAddr:
    """PID + BD_ADDR extraction per passive report (mfr-id 0x0ECB / FDDF same layout)."""

    def test_pid_extracted_from_mfr_data(self):
        """PID is big-endian uint16 at offset 0-1 of payload."""
        parser = JblParser()
        # CID 0x0ECB LE = CB 0E, then PID big-endian 01 1C, then 6-byte BD_ADDR.
        mfr = bytes.fromhex("cb0e011caabbccddeeff")
        ad = _make_ad(
            local_name="JBL Live 660NC",
            manufacturer_data=mfr,
        )
        result = parser.parse(ad)
        assert result.metadata["product_id"] == "011C"
        assert result.metadata["bd_addr"] == "AA:BB:CC:DD:EE:FF"

    def test_pid_extracted_from_fddf_service_data(self):
        parser = JblParser()
        # PID 0x044B + BD_ADDR
        sd = bytes.fromhex("044b112233445566")
        ad = _make_ad(service_data={"fddf": sd})
        result = parser.parse(ad)
        assert result.metadata["product_id"] == "044B"
        assert result.metadata["bd_addr"] == "11:22:33:44:55:66"

    def test_identity_uses_bd_addr_when_present(self):
        """When BD_ADDR is in payload, identity hash uses it (not the volatile BLE MAC)."""
        parser = JblParser()
        mfr = bytes.fromhex("cb0e011caabbccddeeff")
        ad = _make_ad(
            local_name="JBL Live 660NC",
            manufacturer_data=mfr,
            mac_address="FF:FF:FF:FF:FF:FF",  # different from BD_ADDR
        )
        result = parser.parse(ad)
        expected = hashlib.sha256("jbl:AA:BB:CC:DD:EE:FF".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected


class TestJblAvnera:
    def test_matches_avnera_service_uuid(self):
        from adwatch.plugins.jbl import AVNERA_SERVICE_UUID
        parser = JblParser()
        ad = _make_ad(service_uuids=[AVNERA_SERVICE_UUID])
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["avnera_silicon"] is True


class TestJblHarmanCompanyId:
    def test_matches_on_harman_cid_alone(self):
        parser = JblParser()
        # Bare 2-byte CID with no payload — should still match (no PID/BD_ADDR)
        ad = _make_ad(manufacturer_data=b"\xcb\x0e")
        result = parser.parse(ad)
        assert result is not None
        assert "product_id" not in result.metadata
