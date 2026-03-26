"""Fitbit fitness tracker plugin."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

QUALCOMM_COMPANY_ID = 0x000A
KNOWN_OPCODES = {0x01: "advertisement", 0x02: "pairing_request", 0x06: "status"}


@register_parser(
    name="fitbit",
    company_id=QUALCOMM_COMPANY_ID,
    local_name_pattern=r"(?i)^(Fitbit|Charge|Versa|Sense|Inspire|Luxe|Ace)",
    description="Fitbit fitness trackers",
    version="1.0.0",
    core=False,
)
class FitbitParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        is_fitbit_name = raw.local_name and any(
            raw.local_name.lower().startswith(p)
            for p in ("fitbit", "charge", "versa", "sense", "inspire", "luxe", "ace")
        )

        if not raw.manufacturer_data or len(raw.manufacturer_data) < 4:
            if is_fitbit_name:
                return self._presence_only(raw)
            return None

        company_id = int.from_bytes(raw.manufacturer_data[:2], "little")
        if company_id != QUALCOMM_COMPANY_ID:
            if is_fitbit_name:
                return self._presence_only(raw)
            return None

        payload = raw.manufacturer_data[2:]
        opcode = payload[0]

        if not is_fitbit_name and opcode not in KNOWN_OPCODES:
            return None

        metadata = {
            "airlink_opcode": opcode,
            "airlink_state": KNOWN_OPCODES.get(opcode, f"unknown_0x{opcode:02x}"),
        }

        if len(payload) >= 2:
            metadata["device_type"] = payload[1]

        if raw.local_name:
            metadata["device_name"] = raw.local_name

        id_hash = hashlib.sha256(f"{raw.mac_address}:fitbit".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="fitbit",
            beacon_type="fitbit",
            device_class="wearable",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata=metadata,
        )

    def _presence_only(self, raw: RawAdvertisement) -> ParseResult:
        metadata = {}
        if raw.local_name:
            metadata["device_name"] = raw.local_name
        id_hash = hashlib.sha256(f"{raw.mac_address}:fitbit".encode()).hexdigest()[:16]
        return ParseResult(
            parser_name="fitbit",
            beacon_type="fitbit",
            device_class="wearable",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )
