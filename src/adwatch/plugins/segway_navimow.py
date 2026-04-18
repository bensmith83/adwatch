"""Segway Navimow (Ninebot) robotic mower BLE advertisement parser.

Per apk-ble-hunting/reports/segway-mower_passive.md. Unregistered company ID
0x4E42 (ASCII "NB" — Ninebot). Local name carries the serial number in
cleartext; FindMy variant (BLES100) exposes SN as ASCII stream for lost/unpaired
devices.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


NINEBOT_COMPANY_ID = 0x4E42            # ASCII "NB" (LE "BN"), not SIG-registered
MOWER_BLE_TYPE = 0xE0
MOWGATE_BLE_TYPE = 0x23
MIN_PROTOCOL_VERSION = 2


@register_parser(
    name="segway_navimow",
    company_id=NINEBOT_COMPANY_ID,
    local_name_pattern=r"^(PXDA|[A-Z0-9]{6,})$",
    description="Segway Navimow (Ninebot) robotic mowers + MowGate bridges",
    version="1.0.0",
    core=False,
)
class SegwayNavimowParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 5:
            return None
        if int.from_bytes(raw.manufacturer_data[:2], "little") != NINEBOT_COMPANY_ID:
            return None

        payload = raw.manufacturer_payload  # bytes after the 2-byte company ID
        if not payload or len(payload) < 3:
            return None

        ble_type = payload[0]
        protocol_version = payload[1]
        if protocol_version < MIN_PROTOCOL_VERSION:
            return None

        metadata: dict = {
            "ble_type_code": ble_type,
            "protocol_version": protocol_version,
        }

        if ble_type == MOWER_BLE_TYPE:
            metadata["device_class_hint"] = "mower"
        elif ble_type == MOWGATE_BLE_TYPE:
            metadata["device_class_hint"] = "mowgate_bridge"

        # Verify 1's-complement checksum at last byte.
        *body_bytes, checksum = payload
        computed = (~sum(body_bytes)) & 0xFF
        metadata["checksum_valid"] = (computed == checksum)

        # FindMy variant: payload[5] == 1 (offset 7 in raw including company id).
        # Last byte of payload is the 1's-complement checksum — exclude it.
        if len(payload) >= 8 and payload[5] == 1:
            sn_bytes = payload[6:-1]
            try:
                sn = sn_bytes.rstrip(b"\x00").decode("ascii")
                if sn.isprintable():
                    metadata["findmy_mode"] = True
                    metadata["serial_number"] = sn
            except UnicodeDecodeError:
                pass

        name = raw.local_name or ""
        if name and "serial_number" not in metadata:
            metadata["device_name"] = name
            # Local name on Navimow is often the serial itself.
            if name.replace("-", "").isalnum() and len(name) >= 6 and ble_type == MOWER_BLE_TYPE:
                metadata["serial_number"] = name

        if metadata.get("serial_number"):
            id_basis = f"navimow:{metadata['serial_number']}"
        else:
            id_basis = f"navimow:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="segway_navimow",
            beacon_type="segway_navimow",
            device_class="mower",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
