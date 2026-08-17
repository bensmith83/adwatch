"""Tests for the Telit Terminal I/O (TIO) advertisement plugin.

Byte layout per apk-ble-hunting/reports/pari-onecf-paridev_passive.md
(PARI SpiroSense ships the stock Telit TIO advertisement).
"""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.telit_terminal_io import (
    TelitTerminalIOParser,
    TELIT_COMPANY_ID,
    TELIT_UART_SERVICE_UUID,
)


def _make_ad(**kw):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "00:1B:44:11:3A:B7",
        "address_type": "public",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _tio(reserved=0x00, mode=1, conn_requested=0):
    return bytes([0x8F, 0x00, 0x09, 0xB0, reserved, mode, conn_requested])


def _register(registry):
    @register_parser(
        name="telit_terminal_io",
        company_id=TELIT_COMPANY_ID,
        service_uuid=TELIT_UART_SERVICE_UUID,
        description="Telit TIO",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(TelitTerminalIOParser):
        pass

    return _P


class TestTelitMatching:
    def test_matches_telit_company_id(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(manufacturer_data=_tio()))) == 1

    def test_matches_uart_service_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[TELIT_UART_SERVICE_UUID])
        assert len(registry.match(ad)) == 1

    def test_matches_short_uart_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(service_uuids=["fefb"]))) == 1

    def test_unrelated_does_not_match(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=bytes([0x4C, 0x00, 0x09, 0xB0]))
        assert registry.match(ad) == []


class TestTelitTioDecode:
    def test_decodes_functional_mode(self):
        result = TelitTerminalIOParser().parse(_make_ad(manufacturer_data=_tio(mode=1)))
        assert result is not None
        assert result.metadata["operation_mode"] == 1
        assert result.metadata["operation_mode_name"] == "Functional"
        assert result.metadata["connection_requested"] is False
        assert result.metadata["tio_advertisement"] is True

    def test_decodes_bonding_only_mode(self):
        result = TelitTerminalIOParser().parse(_make_ad(manufacturer_data=_tio(mode=0)))
        assert result.metadata["operation_mode_name"] == "BondingOnly"

    def test_decodes_bondable_functional_mode(self):
        result = TelitTerminalIOParser().parse(_make_ad(manufacturer_data=_tio(mode=16)))
        assert result.metadata["operation_mode_name"] == "BondableFunctional"

    def test_unknown_mode_value(self):
        result = TelitTerminalIOParser().parse(_make_ad(manufacturer_data=_tio(mode=7)))
        assert result.metadata["operation_mode"] == 7
        assert result.metadata["operation_mode_name"] == "unknown"

    def test_connection_requested_flag(self):
        result = TelitTerminalIOParser().parse(
            _make_ad(manufacturer_data=_tio(conn_requested=1))
        )
        assert result.metadata["connection_requested"] is True

    def test_connection_requested_only_when_exactly_one(self):
        result = TelitTerminalIOParser().parse(
            _make_ad(manufacturer_data=_tio(conn_requested=2))
        )
        assert result.metadata["connection_requested"] is False

    def test_wrong_first_marker_not_decoded(self):
        ad = _make_ad(manufacturer_data=bytes([0x8F, 0x00, 0x08, 0xB0, 0, 1, 0]))
        assert TelitTerminalIOParser().parse(ad) is None

    def test_wrong_second_marker_not_decoded(self):
        ad = _make_ad(manufacturer_data=bytes([0x8F, 0x00, 0x09, 0xB1, 0, 1, 0]))
        assert TelitTerminalIOParser().parse(ad) is None

    def test_too_short_payload_not_decoded(self):
        ad = _make_ad(manufacturer_data=bytes([0x8F, 0x00, 0x09, 0xB0, 0x00, 0x01]))
        assert TelitTerminalIOParser().parse(ad) is None

    def test_wrong_company_id_not_decoded(self):
        ad = _make_ad(manufacturer_data=bytes([0x4C, 0x00, 0x09, 0xB0, 0, 1, 0]))
        assert TelitTerminalIOParser().parse(ad) is None

    def test_uuid_only_detection_without_telemetry(self):
        result = TelitTerminalIOParser().parse(_make_ad(service_uuids=["fefb"]))
        assert result is not None
        assert result.metadata["tio_advertisement"] is False
        assert "operation_mode" not in result.metadata

    def test_returns_none_for_unrelated(self):
        assert TelitTerminalIOParser().parse(
            _make_ad(manufacturer_data=bytes([0x4C, 0x00, 0x02, 0x15]))
        ) is None


class TestTelitIdentityAndBasics:
    def test_identity_from_mac(self):
        ad = _make_ad(manufacturer_data=_tio())
        result = TelitTerminalIOParser().parse(ad)
        expected = hashlib.sha256(
            f"telit_tio:{ad.mac_address}".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identity_stable_across_state_change(self):
        a = _make_ad(manufacturer_data=_tio(mode=0, conn_requested=0))
        b = _make_ad(manufacturer_data=_tio(mode=16, conn_requested=1))
        assert TelitTerminalIOParser().parse(a).identifier_hash == \
            TelitTerminalIOParser().parse(b).identifier_hash

    def test_basics(self):
        result = TelitTerminalIOParser().parse(_make_ad(manufacturer_data=_tio()))
        assert result.parser_name == "telit_terminal_io"
        assert result.beacon_type == "telit_terminal_io"
        assert result.device_class == "module"
        assert result.metadata["vendor"] == "Telit"
        assert result.metadata["protocol"] == "Terminal I/O"

    def test_local_name_recorded(self):
        ad = _make_ad(manufacturer_data=_tio(), local_name="SpiroSense")
        assert TelitTerminalIOParser().parse(ad).metadata["device_name"] == "SpiroSense"

    def test_company_id_constant(self):
        assert TELIT_COMPANY_ID == 0x008F
