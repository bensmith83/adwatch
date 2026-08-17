"""Telit Terminal I/O (TIO) advertisement plugin.

Per apk-ble-hunting/reports/pari-onecf-paridev_passive.md — the PARI
SpiroSense spirometer ships the stock Telit TIO advertisement decoded by
``com.telit.terminalio.TIOAdvertisement.evaluateData``.  The shape is
vendor-generic: any Telit BLE module running Terminal I/O advertises it, so
this plugin is named for the protocol rather than for one product.

Offsets are within ``RawAdvertisement.manufacturer_payload`` (the report's
indices minus the 2-byte company ID ``0x008F``):

    0    TIO marker, must be 0x09
    1    TIO marker, must be 0xB0
    2    reserved (not checked by the SDK)
    3    operation mode — 0 BondingOnly / 1 Functional / 16 BondableFunctional
    4    connection requested — ``== 1`` means the device wants a connection

The advertisement carries operational state only: no serial, no telemetry.
Devices also advertise the Telit UART service ``0000FEFB-…``.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

TELIT_COMPANY_ID = 0x008F
TELIT_UART_SERVICE_UUID = "0000fefb-0000-1000-8000-00805f9b34fb"

TIO_MARKER = (0x09, 0xB0)

OPERATION_MODES = {
    0: "BondingOnly",
    1: "Functional",
    16: "BondableFunctional",
}

# marker[2] + reserved + mode + connection-requested (report: full length >= 7)
_MIN_PAYLOAD_LEN = 5

_UART_UUID_FORMS = {TELIT_UART_SERVICE_UUID, "fefb"}


@register_parser(
    name="telit_terminal_io",
    company_id=TELIT_COMPANY_ID,
    service_uuid=TELIT_UART_SERVICE_UUID,
    description="Telit Terminal I/O module advertisements",
    version="1.0.0",
    core=False,
)
class TelitTerminalIOParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        advertised = {u.lower() for u in (raw.service_uuids or [])}
        uart_uuid_hit = bool(advertised & _UART_UUID_FORMS)

        payload = (
            raw.manufacturer_payload
            if raw.company_id == TELIT_COMPANY_ID
            else None
        )
        tio_hit = bool(
            payload
            and len(payload) >= _MIN_PAYLOAD_LEN
            and (payload[0], payload[1]) == TIO_MARKER
        )

        if not (tio_hit or uart_uuid_hit):
            return None

        metadata: dict = {
            "vendor": "Telit",
            "protocol": "Terminal I/O",
            "tio_advertisement": tio_hit,
        }
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        if tio_hit:
            mode = payload[3]
            metadata["operation_mode"] = mode
            metadata["operation_mode_name"] = OPERATION_MODES.get(mode, "unknown")
            metadata["connection_requested"] = payload[4] == 1

        id_hash = hashlib.sha256(
            f"telit_tio:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="telit_terminal_io",
            beacon_type="telit_terminal_io",
            device_class="module",
            identifier_hash=id_hash,
            raw_payload_hex=raw.manufacturer_data.hex() if raw.manufacturer_data else "",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
