"""Oral-B Toothbrush BLE advertisement parser."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

ORALB_COMPANY_ID = 0x00DC
MIN_PAYLOAD_LEN = 7

STATES = {
    0x02: "idle",
    0x03: "running",
    0x04: "charging",
    0x06: "stage_completed",
    0x07: "shutdown",
}

PRESSURES = {
    0x00: "normal",
    0x01: "high",
    0x03: "overpressure",
}

MODES = {
    0x00: "off",
    0x01: "daily_clean",
    0x02: "sensitive",
    0x03: "massage",
    0x04: "whitening",
    0x05: "deep_clean",
    0x06: "tongue_cleaning",
    0x07: "turbo",
}


@register_parser(
    name="oralb",
    company_id=ORALB_COMPANY_ID,
    local_name_pattern=r"Oral-B",
    description="Oral-B Toothbrush",
    version="1.0.0",
    core=False,
)
class OralBParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 2:
            return None

        company_id = int.from_bytes(raw.manufacturer_data[:2], "little")
        if company_id != ORALB_COMPANY_ID:
            return None

        payload = raw.manufacturer_data[2:]
        if len(payload) < MIN_PAYLOAD_LEN:
            return None

        protocol_version = payload[0]
        state = STATES.get(payload[1], "unknown")
        pressure = PRESSURES.get(payload[2], "unknown")
        minutes = payload[3]
        seconds = payload[4]
        mode = MODES.get(payload[5], "unknown")
        sector = payload[6]

        id_hash = hashlib.sha256(raw.mac_address.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="oralb",
            beacon_type="oralb",
            device_class="appliance",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata={
                "protocol_version": protocol_version,
                "state": state,
                "pressure": pressure,
                "brushing_time_seconds": minutes * 60 + seconds,
                "mode": mode,
                "sector": sector,
            },
        )
