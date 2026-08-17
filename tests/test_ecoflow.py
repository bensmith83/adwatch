"""Tests for EcoFlow portable power station plugin."""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import ParserRegistry, register_parser

# RED phase — this import will fail until the plugin exists
from adwatch.plugins.ecoflow import (
    EcoFlowParser,
    ECOFLOW_COMPANY_ID,
    ECOFLOW_COMPANY_IDS,
)


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


def _build_full_payload(
    serial=b"R331ABCDEFGHIJKL",
    status=0x55,
    product_type=0x02,
    caps=0x47,
    protocol_version=1,
    charge_byte=0x00,
    config_byte=0x00,
):
    """Build a full 23-byte EcoFlow manufacturer data payload (after company ID).

    Payload offsets (report offsets are relative to the AD length byte M; the
    company ID sits at M+2..M+3, so payload index j == report offset M+4+j):

      payload[0]      protocol/version byte      (M+4)
      payload[1:17]   16-byte ASCII serial       (M+5..M+20)
      payload[17]     SoC bits0-6 | dormant bit7 (M+21)
      payload[18]     model / OTA state          (M+22)
      payload[19]     charge bit2 / sleep bits0-1(M+23)
      payload[20]     config/pairing state (V1)  (M+24)
      payload[21]     reserved                   (M+25)
      payload[22]     security capability bits   (M+26)
    """
    # pad/truncate serial to 16 bytes
    serial = serial[:16].ljust(16, b"\x00")
    payload = bytes([protocol_version]) + serial + bytes([status, product_type])
    payload += bytes([charge_byte, config_byte, 0x00])
    payload += bytes([caps])
    return payload


def _make_mfr_data(payload):
    """Prepend little-endian company ID to payload."""
    return struct.pack("<H", ECOFLOW_COMPANY_ID) + payload


class TestEcoFlowParser:
    def test_full_payload_parses(self):
        """Valid full payload parses serial, model, active, caps."""
        payload = _build_full_payload()
        ad = _make_ad(manufacturer_data=_make_mfr_data(payload))
        parser = EcoFlowParser()
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "ecoflow"
        assert result.beacon_type == "ecoflow"
        assert result.device_class == "power"
        assert result.metadata["serial_number"] == "R331ABCDEFGHIJKL"
        assert result.metadata["device_model"] == "DELTA 2"
        assert result.metadata["active"] is True
        assert result.metadata["product_type"] == 0x02
        assert result.metadata["protocol_version"] == 1

    def test_model_delta2_r331(self):
        """R331 prefix → DELTA 2."""
        payload = _build_full_payload(serial=b"R331XXXXXXXXXXXX")
        ad = _make_ad(manufacturer_data=_make_mfr_data(payload))
        result = EcoFlowParser().parse(ad)
        assert result.metadata["device_model"] == "DELTA 2"

    def test_model_powerstream_hw51(self):
        """HW51 prefix → PowerStream."""
        payload = _build_full_payload(serial=b"HW51XXXXXXXXXXXX")
        ad = _make_ad(manufacturer_data=_make_mfr_data(payload))
        result = EcoFlowParser().parse(ad)
        assert result.metadata["device_model"] == "PowerStream"

    def test_model_delta_mini_db(self):
        """DB prefix → DELTA mini."""
        payload = _build_full_payload(serial=b"DB12XXXXXXXXXXXX")
        ad = _make_ad(manufacturer_data=_make_mfr_data(payload))
        result = EcoFlowParser().parse(ad)
        assert result.metadata["device_model"] == "DELTA mini"

    def test_model_delta_pro_3(self):
        """MR51 prefix → DELTA Pro 3."""
        payload = _build_full_payload(serial=b"MR51XXXXXXXXXXXX")
        ad = _make_ad(manufacturer_data=_make_mfr_data(payload))
        result = EcoFlowParser().parse(ad)
        assert result.metadata["device_model"] == "DELTA Pro 3"

    def test_unknown_serial_prefix(self):
        """Unknown serial prefix returns 'Unknown EcoFlow'."""
        payload = _build_full_payload(serial=b"ZZ99XXXXXXXXXXXX")
        ad = _make_ad(manufacturer_data=_make_mfr_data(payload))
        result = EcoFlowParser().parse(ad)
        assert result.metadata["device_model"] == "Unknown EcoFlow"

    def test_short_payload_parses_available(self):
        """Short payload (< 20 bytes) still parses what's available."""
        # Only protocol_version + serial (17 bytes)
        payload = bytes([0x02]) + b"R601ABCDEFGHIJKL"
        assert len(payload) == 17
        ad = _make_ad(manufacturer_data=_make_mfr_data(payload))
        result = EcoFlowParser().parse(ad)
        assert result is not None
        assert result.metadata["protocol_version"] == 2
        assert result.metadata["serial_number"] == "R601ABCDEFGHIJKL"
        assert result.metadata["device_model"] == "RIVER 2"
        # status/product_type should not be present
        assert "active" not in result.metadata
        assert "product_type" not in result.metadata

    def test_soc_and_dormancy_from_status_byte(self):
        """payload[17] (report M+21): bits0-6 = SoC %, bit7 = dormancy flag."""
        # 0x55 = 0b0101_0101 → SoC 85%, not dormant
        payload = _build_full_payload(status=0x55)
        ad = _make_ad(manufacturer_data=_make_mfr_data(payload))
        result = EcoFlowParser().parse(ad)
        assert result.metadata["state_of_charge_pct"] == 85
        assert result.metadata["dormant"] is False
        assert result.metadata["active"] is True

        # 0xD5 = dormancy bit set, same SoC
        payload = _build_full_payload(status=0xD5)
        ad = _make_ad(manufacturer_data=_make_mfr_data(payload))
        result = EcoFlowParser().parse(ad)
        assert result.metadata["state_of_charge_pct"] == 85
        assert result.metadata["dormant"] is True
        assert result.metadata["active"] is False

        # 0x00 → 0% and awake
        payload = _build_full_payload(status=0x00)
        ad = _make_ad(manufacturer_data=_make_mfr_data(payload))
        result = EcoFlowParser().parse(ad)
        assert result.metadata["state_of_charge_pct"] == 0
        assert result.metadata["dormant"] is False

    def test_soc_out_of_range_is_dropped(self):
        """A bits0-6 value above 100 is not a plausible SoC and is omitted."""
        payload = _build_full_payload(status=0x7F)  # 127
        ad = _make_ad(manufacturer_data=_make_mfr_data(payload))
        result = EcoFlowParser().parse(ad)
        assert "state_of_charge_pct" not in result.metadata
        assert result.metadata["dormant"] is False

    def test_capability_flags(self):
        """Capability flags are parsed correctly from byte 22."""
        # caps=0x47: encrypted(1), verification(1), verified(1), enc_type=0, 5ghz(1)
        # 0x47 = 0b01000111
        payload = _build_full_payload(caps=0x47)
        ad = _make_ad(manufacturer_data=_make_mfr_data(payload))
        result = EcoFlowParser().parse(ad)
        assert result.metadata["encrypted"] is True
        assert result.metadata["supports_verification"] is True
        assert result.metadata["verified"] is True
        assert result.metadata["encryption_type"] == 0
        assert result.metadata["supports_5ghz"] is True

    def test_capability_flags_encryption_type(self):
        """Encryption type extracted from bits 3-5."""
        # caps=0x28: enc_type=5 (0b101 << 3 = 0x28)
        payload = _build_full_payload(caps=0x28)
        ad = _make_ad(manufacturer_data=_make_mfr_data(payload))
        result = EcoFlowParser().parse(ad)
        assert result.metadata["encrypted"] is False
        assert result.metadata["encryption_type"] == 5
        assert result.metadata["supports_5ghz"] is False

    def test_too_short_returns_none(self):
        """Manufacturer data < 4 bytes returns None."""
        ad = _make_ad(manufacturer_data=b"\xb5\xb5")
        result = EcoFlowParser().parse(ad)
        assert result is None

    def test_no_manufacturer_data_returns_none(self):
        """No manufacturer data returns None."""
        ad = _make_ad(manufacturer_data=None)
        result = EcoFlowParser().parse(ad)
        assert result is None

    def test_wrong_company_id_returns_none(self):
        """Wrong company ID returns None."""
        payload = _build_full_payload()
        mfr_data = struct.pack("<H", 0x1234) + payload
        ad = _make_ad(manufacturer_data=mfr_data)
        result = EcoFlowParser().parse(ad)
        assert result is None

    def test_identity_hash_prefers_serial(self):
        """Serial number is broadcast in the clear and survives MAC rotation."""
        payload = _build_full_payload(serial=b"R331ABCDEFGHIJKL")
        expected = hashlib.sha256(b"ecoflow:R331ABCDEFGHIJKL").hexdigest()[:16]

        first = EcoFlowParser().parse(
            _make_ad(manufacturer_data=_make_mfr_data(payload),
                     mac_address="11:22:33:44:55:66")
        )
        second = EcoFlowParser().parse(
            _make_ad(manufacturer_data=_make_mfr_data(payload),
                     mac_address="AA:BB:CC:DD:EE:FF")
        )
        assert first.identifier_hash == expected
        # MAC rotation must not change the identity
        assert second.identifier_hash == expected

    def test_identity_hash_falls_back_to_mac(self):
        """Without a usable serial the MAC-based hash is kept."""
        # 4-byte payload: no serial field available
        ad = _make_ad(
            manufacturer_data=_make_mfr_data(b"\xa1\x00"),
            mac_address="11:22:33:44:55:66",
        )
        result = EcoFlowParser().parse(ad)
        expected = hashlib.sha256(b"11:22:33:44:55:66:ecoflow").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_registry_match_company_id(self):
        """Registry matches on company_id 0xB5B5."""
        registry = ParserRegistry()

        @register_parser(
            name="ecoflow", company_id=ECOFLOW_COMPANY_ID,
            local_name_pattern=r"^EF-",
            description="EcoFlow", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(EcoFlowParser):
            pass

        payload = _build_full_payload()
        ad = _make_ad(manufacturer_data=_make_mfr_data(payload))
        matches = registry.match(ad)
        assert len(matches) == 1

    def test_registry_match_local_name(self):
        """Registry matches on local name 'EF-...'."""
        registry = ParserRegistry()

        @register_parser(
            name="ecoflow", company_id=ECOFLOW_COMPANY_ID,
            local_name_pattern=r"^EF-",
            description="EcoFlow", version="1.0.0", core=False, registry=registry,
        )
        class TestParser(EcoFlowParser):
            pass

        ad = _make_ad(local_name="EF-DELTA2-ABC123")
        matches = registry.match(ad)
        assert len(matches) == 1

    def test_raw_payload_hex(self):
        """raw_payload_hex contains the payload after company ID."""
        payload = _build_full_payload()
        ad = _make_ad(manufacturer_data=_make_mfr_data(payload))
        result = EcoFlowParser().parse(ad)
        assert result.raw_payload_hex == payload.hex()


class TestEcoFlowReportEnrichment:
    """Fields verified against reports/ecoflow_passive.md (Stage 4b)."""

    def test_alternate_company_ids_are_registered(self):
        """The app installs scan filters for 0xB5B5, 0xA4A8 and 0x0BA9."""
        assert set(ECOFLOW_COMPANY_IDS) == {0xB5B5, 0xA4A8, 0x0BA9}
        assert ECOFLOW_COMPANY_ID == 0xB5B5

    @pytest.mark.parametrize("cid", [0xB5B5, 0xA4A8, 0x0BA9])
    def test_parses_each_company_id(self, cid):
        payload = _build_full_payload()
        ad = _make_ad(manufacturer_data=struct.pack("<H", cid) + payload)
        result = EcoFlowParser().parse(ad)
        assert result is not None
        assert result.metadata["company_id"] == cid
        assert result.metadata["serial_number"] == "R331ABCDEFGHIJKL"

    @pytest.mark.parametrize("cid", [0xB5B5, 0xA4A8, 0x0BA9])
    def test_registry_matches_each_company_id(self, cid):
        registry = ParserRegistry()

        @register_parser(
            name="ecoflow", company_id=ECOFLOW_COMPANY_IDS,
            local_name_pattern=r"^(EF-|ECO_HOME$)",
            description="EcoFlow", version="1.0.0", core=False, registry=registry,
        )
        class _P(EcoFlowParser):
            pass

        ad = _make_ad(manufacturer_data=struct.pack("<H", cid) + _build_full_payload())
        assert len(registry.match(ad)) == 1

    def test_charging_bit_is_bit2_of_m23(self):
        """report M+23 (payload[19]) bit2 = charging."""
        payload = _build_full_payload(charge_byte=0x04)
        result = EcoFlowParser().parse(_make_ad(manufacturer_data=_make_mfr_data(payload)))
        assert result.metadata["charging"] is True

        payload = _build_full_payload(charge_byte=0x00)
        result = EcoFlowParser().parse(_make_ad(manufacturer_data=_make_mfr_data(payload)))
        assert result.metadata["charging"] is False

    def test_sleeping_when_low_two_bits_equal_one(self):
        """report M+23: (x & 3) != 1 means NOT sleeping."""
        # 0x01 → (x & 3) == 1 → sleeping
        payload = _build_full_payload(charge_byte=0x01)
        result = EcoFlowParser().parse(_make_ad(manufacturer_data=_make_mfr_data(payload)))
        assert result.metadata["sleeping"] is True

        # 0x02 → (x & 3) == 2 → awake
        payload = _build_full_payload(charge_byte=0x02)
        result = EcoFlowParser().parse(_make_ad(manufacturer_data=_make_mfr_data(payload)))
        assert result.metadata["sleeping"] is False

    def test_ota_bits_from_model_byte(self):
        """report M+22 (payload[18]): bits7-6 upgradeStatus, bits5-0 configState."""
        # 0b10_001010 = 0x8A → upgrade 2, config 10
        payload = _build_full_payload(product_type=0x8A)
        result = EcoFlowParser().parse(_make_ad(manufacturer_data=_make_mfr_data(payload)))
        assert result.metadata["product_type"] == 0x8A
        assert result.metadata["upgrade_status"] == 2
        assert result.metadata["config_state"] == 0x0A

    def test_v1_config_state_byte(self):
        """report M+24 (payload[20]) carries configState for the V1 families."""
        payload = _build_full_payload(config_byte=0x07)
        result = EcoFlowParser().parse(_make_ad(manufacturer_data=_make_mfr_data(payload)))
        assert result.metadata["config_state_v1"] == 0x07

    def test_device_add_flag_from_status_byte(self):
        """report: u0/p0 families read M+21 bit7 as deviceAddFlag, bits6-0 as state."""
        payload = _build_full_payload(status=0xC3)
        result = EcoFlowParser().parse(_make_ad(manufacturer_data=_make_mfr_data(payload)))
        assert result.metadata["device_add_flag"] is True
        assert result.metadata["device_add_state_code"] == 0x43

    def test_ssl_type_bit7_of_caps(self):
        """report M+26 bit7 feeds sslType."""
        payload = _build_full_payload(caps=0x80)
        result = EcoFlowParser().parse(_make_ad(manufacturer_data=_make_mfr_data(payload)))
        assert result.metadata["ssl_type"] == 1

        payload = _build_full_payload(caps=0x00)
        result = EcoFlowParser().parse(_make_ad(manufacturer_data=_make_mfr_data(payload)))
        assert result.metadata["ssl_type"] == 0

    def test_protocol_v2_flag(self):
        """isBle() gates protocol V2 on the version byte being >= 0xA1."""
        payload = _build_full_payload(protocol_version=0xA1)
        result = EcoFlowParser().parse(_make_ad(manufacturer_data=_make_mfr_data(payload)))
        assert result.metadata["protocol_v2"] is True

        payload = _build_full_payload(protocol_version=0x01)
        result = EcoFlowParser().parse(_make_ad(manufacturer_data=_make_mfr_data(payload)))
        assert result.metadata["protocol_v2"] is False

    def test_eco_home_name_only_device(self):
        """`ECO_HOME` is an exact-match name with no telemetry payload."""
        ad = _make_ad(local_name="ECO_HOME")
        result = EcoFlowParser().parse(ad)
        assert result is not None
        assert result.beacon_type == "ecoflow_home"
        assert result.device_class == "power"
        assert result.metadata["name_only"] is True
        assert result.metadata["product_type_code"] == 1001
        assert result.identifier_hash == hashlib.sha256(
            b"AA:BB:CC:DD:EE:FF:ecoflow"
        ).hexdigest()[:16]

    def test_eco_home_registry_match(self):
        registry = ParserRegistry()

        @register_parser(
            name="ecoflow", company_id=ECOFLOW_COMPANY_IDS,
            local_name_pattern=r"^(EF-|ECO_HOME$)",
            description="EcoFlow", version="1.0.0", core=False, registry=registry,
        )
        class _P(EcoFlowParser):
            pass

        assert len(registry.match(_make_ad(local_name="ECO_HOME"))) == 1
        # Must not swallow unrelated names that merely contain the token
        assert len(registry.match(_make_ad(local_name="MY_ECO_HOMER"))) == 0

    def test_serial_with_trailing_padding(self):
        """Serial is ASCII, NUL/space padded."""
        payload = _build_full_payload(serial=b"R601AB\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
        result = EcoFlowParser().parse(_make_ad(manufacturer_data=_make_mfr_data(payload)))
        assert result.metadata["serial_number"] == "R601AB"
        assert result.metadata["device_model"] == "RIVER 2"

    def test_non_ascii_serial_falls_back_to_hex(self):
        payload = _build_full_payload(serial=bytes(range(0x80, 0x90)))
        result = EcoFlowParser().parse(_make_ad(manufacturer_data=_make_mfr_data(payload)))
        assert result.metadata["serial_number"] == bytes(range(0x80, 0x90)).hex()

    def test_fff6_service_data_alone_does_not_match(self):
        """0xFFF6 is the Matter commissionable UUID — too generic to claim."""
        registry = ParserRegistry()

        @register_parser(
            name="ecoflow", company_id=ECOFLOW_COMPANY_IDS,
            local_name_pattern=r"^(EF-|ECO_HOME$)",
            description="EcoFlow", version="1.0.0", core=False, registry=registry,
        )
        class _P(EcoFlowParser):
            pass

        ad = _make_ad(service_data={"fff6": b"\x00\x00\x0f\x5f\x23\x00\x00\x00"})
        assert registry.match(ad) == []
