"""Victron Energy Instant Readout plugin."""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

VICTRON_COMPANY_ID = 0x02E1

RECORD_TYPES = {
    0x01: "Solar Charger",
    0x02: "Battery Monitor",
    0x03: "Inverter",
    0x04: "DC/DC Converter",
    0x05: "SmartShunt",
    0x06: "Inverter RS",
    0x07: "GX Device",
    0x08: "AC Charger",
    0x09: "Smart Battery Protect",
    0x0A: "Lynx Smart BMS",
    0x0B: "Multi RS",
    0x0C: "VE.Bus",
    0x0D: "DC Energy Meter",
    0x0F: "Orion XS",
}


@register_parser(
    name="victron_energy",
    company_id=VICTRON_COMPANY_ID,
    description="Victron Energy Instant Readout",
    version="1.0.0",
    core=False,
)
class VictronEnergyParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 4:
            return None

        payload = raw.manufacturer_payload
        if not payload or len(payload) < 5:
            return None

        prefix = payload[0]
        if prefix != 0x10:
            return None

        model_id = struct.unpack_from("<H", payload, 2)[0]
        record_type = payload[4]
        device_type = RECORD_TYPES.get(record_type, "Unknown")

        metadata: dict = {
            "model_id": model_id,
            "record_type": record_type,
            "device_type": device_type,
        }

        if len(payload) >= 7:
            metadata["data_counter"] = struct.unpack_from("<H", payload, 5)[0]

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:{model_id}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="victron_energy",
            beacon_type="victron_energy",
            device_class="energy",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
