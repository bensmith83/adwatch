"""Volvo vehicle BLE phone-key advertisement parser.

Per apk-ble-hunting/reports/volvo-vcc_passive.md. Volvo uses Apple's iBeacon
wrapper (company ID 0x004C) with a hardcoded fleet-wide proximity UUID
`E20A39F4-73F5-4BC4-1864-17D1AD07A962`. Major/minor encode per-vehicle
Session-Key-Index (SKI) bytes 0-3.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


VOLVO_IBEACON_UUID = "e20a39f473f54bc4186417d1ad07a962"
APPLE_COMPANY_ID = 0x004C


@register_parser(
    name="volvo",
    local_name_pattern=r"(?i)^Volvo",
    description="Volvo vehicle phone-key (iBeacon) advertisements",
    version="1.0.0",
    core=False,
)
class VolvoParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        name = raw.local_name or ""
        name_match = name.lower().startswith("volvo")

        proximity_match = False
        major = None
        minor = None
        payload = raw.manufacturer_payload
        if (raw.manufacturer_data
                and int.from_bytes(raw.manufacturer_data[:2], "little") == APPLE_COMPANY_ID
                and payload
                and len(payload) >= 23
                and payload[0] == 0x02
                and payload[1] == 0x15):
            proximity_uuid_hex = payload[2:18].hex()
            if proximity_uuid_hex == VOLVO_IBEACON_UUID:
                proximity_match = True
                major = int.from_bytes(payload[18:20], "big")
                minor = int.from_bytes(payload[20:22], "big")

        if not (name_match or proximity_match):
            return None

        metadata: dict = {}
        if name:
            metadata["device_name"] = name
        if proximity_match:
            metadata["volvo_proximity_match"] = True
            metadata["major"] = major
            metadata["minor"] = minor
            metadata["ski_fragment_hex"] = f"{major:04x}{minor:04x}"

        ski = metadata.get("ski_fragment_hex")
        if ski:
            id_basis = f"volvo:{ski}"
        else:
            id_basis = f"volvo:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="volvo",
            beacon_type="volvo",
            device_class="vehicle",
            identifier_hash=id_hash,
            raw_payload_hex=(payload or b"").hex(),
            metadata=metadata,
        )
