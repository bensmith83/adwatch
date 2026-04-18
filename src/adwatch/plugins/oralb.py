"""Oral-B Toothbrush BLE advertisement parser.

Byte layout per apk-ble-hunting/reports/pg-oralb-oralbapp_passive.md
(Advertisement.java:128-148). Payload offsets below are relative to the
mfr-data payload (after the 2-byte company ID 0x00DC is stripped).
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

ORALB_COMPANY_ID = 0x00DC
MIN_PAYLOAD_LEN = 5  # up to deviceState; timing/mode fields require more

# Device state (byte offset 5 in the AD structure, payload[3]).
DEVICE_STATES = {
    0x00: "UNKNOWN",
    0x01: "INIT",
    0x02: "IDLE",
    0x03: "RUN",
    0x04: "CHARGE",
    0x05: "SETUP",
    0x06: "FLIGHT_MENU",
    0x07: "CHARGE_FORBIDDEN",
    0x08: "PRE_RUN",
    0x09: "PAUSE",
    0x0A: "POST_BRUSHING_STATISTICS",
    0x73: "SLEEP",
    0x74: "TRANSPORT",
}

# Device type (byte offset 3 in payload). 37 models per passive report.
DEVICE_TYPES = {
    0x00: "D36_X_MODE",        0x01: "D36_6_MODE",       0x02: "D36_5_MODE",
    0x20: "D701_X_MODE",       0x21: "D701_6_MODE",      0x22: "D701_5_MODE",
    0x27: "D700_5_MODE",       0x28: "D700_4_MODE",      0x29: "D700_6_MODE",
    0x30: "SONOS_X_MODE",      0x31: "SONOS",            0x32: "SONOS_BIG_TI",
    0x34: "SONOS_G4",          0x35: "SONOS_G5",         0x36: "SONOS_EPLATFORM",
    0x3F: "D36_EXPERIMENTAL",
    0x40: "D21_X_MODE",        0x41: "D21_4_MODE",       0x42: "D21_3_MODE",
    0x43: "D21_2A_MODE",       0x44: "D21_2B_MODE",      0x45: "D21_3_MODE_WHITENING",
    0x46: "D21_1_MODE",
    0x50: "D601_X_MODE",       0x51: "D601_5_MODE",      0x52: "D601_4_MODE",
    0x53: "D601_3A_MODE",      0x54: "D601_2A_MODE",     0x55: "D601_2B_MODE",
    0x56: "D601_3B_MODE",      0x57: "D601_1_MODE",
    0x70: "D706_X_MODE",       0x71: "D706_6_MODE",      0x72: "D706_5_MODE",
    0x7F: "D21_EXPERIMENTAL",
    0xFF: "EXPERIMENTAL",
}


@register_parser(
    name="oralb",
    company_id=ORALB_COMPANY_ID,
    local_name_pattern=r"Oral-B",
    description="Oral-B Toothbrush",
    version="2.0.0",
    core=False,
)
class OralBParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 2:
            return None
        if int.from_bytes(raw.manufacturer_data[:2], "little") != ORALB_COMPANY_ID:
            return None

        payload = raw.manufacturer_payload
        if not payload or len(payload) < MIN_PAYLOAD_LEN:
            return None

        protocol_version = payload[0]
        device_type_code = payload[1]
        software_version = payload[2]
        device_state_code = payload[3]
        status_byte = payload[4]

        metadata: dict = {
            "protocol_version": protocol_version,
            "device_type_code": device_type_code,
            "device_type": DEVICE_TYPES.get(device_type_code, f"UNKNOWN_0x{device_type_code:02X}"),
            "software_version": software_version,
            "device_state_code": device_state_code,
            "device_state": DEVICE_STATES.get(device_state_code, f"UNKNOWN_0x{device_state_code:02X}"),
            "pressure_high": bool(status_byte & 0x80),
            "power_button_pressed": bool(status_byte & 0x08),
            "mode_button_pressed": bool(status_byte & 0x04),
        }

        if len(payload) >= 7:
            metadata["brushing_time_seconds"] = payload[5] * 60 + payload[6]
        if len(payload) >= 8:
            metadata["brush_mode"] = payload[7]
        if len(payload) >= 9:
            metadata["brush_progress"] = payload[8]
        if len(payload) >= 10:
            metadata["quadrant_completion_or_subtype"] = payload[9]
        if len(payload) >= 11:
            metadata["total_quadrants"] = payload[10]

        id_hash = hashlib.sha256(raw.mac_address.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="oralb",
            beacon_type="oralb",
            device_class="appliance",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata=metadata,
        )
