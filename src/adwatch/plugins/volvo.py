"""Volvo vehicle BLE phone-key advertisement parser.

Per apk-ble-hunting/reports/volvo-vcc_passive.md. Volvo uses Apple's iBeacon
wrapper (company ID 0x004C) with a hardcoded fleet-wide proximity UUID
`E20A39F4-73F5-4BC4-1864-17D1AD07A962`. Major/minor encode per-vehicle
Session-Key-Index (SKI) bytes 0-3.

Registration note: we register on the Apple company ID so every iBeacon
routes through here — the iBeacon proximity UUID is the real Volvo signal.
`parse()` gates on that UUID and returns None for any non-Volvo iBeacon.
Local name is used only as enrichment (serial/model), never as the sole
classification signal.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


VOLVO_IBEACON_UUID = "e20a39f473f54bc4186417d1ad07a962"
APPLE_COMPANY_ID = 0x004C


@register_parser(
    name="volvo",
    company_id=APPLE_COMPANY_ID,
    description="Volvo vehicle phone-key (iBeacon) advertisements",
    version="1.1.0",
    core=False,
)
class VolvoParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        payload = raw.manufacturer_payload
        if not (raw.manufacturer_data
                and int.from_bytes(raw.manufacturer_data[:2], "little") == APPLE_COMPANY_ID
                and payload
                and len(payload) >= 23
                and payload[0] == 0x02
                and payload[1] == 0x15):
            return None

        if payload[2:18].hex() != VOLVO_IBEACON_UUID:
            return None

        major = int.from_bytes(payload[18:20], "big")
        minor = int.from_bytes(payload[20:22], "big")

        metadata: dict = {
            "volvo_proximity_match": True,
            "major": major,
            "minor": minor,
            "ski_fragment_hex": f"{major:04x}{minor:04x}",
        }

        name = raw.local_name or ""
        if name:
            metadata["device_name"] = name

        id_hash = hashlib.sha256(
            f"volvo:{metadata['ski_fragment_hex']}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="volvo",
            beacon_type="volvo",
            device_class="vehicle",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata=metadata,
        )
