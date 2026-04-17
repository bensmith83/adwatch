"""GD Midea smart-appliance BLE advertisement parser.

Midea Wi-Fi appliances (air conditioners, dehumidifiers, washers, etc. —
also sold as Comfee, Inventor EVO, and Toshiba HA) broadcast a BLE frame
carrying their 14-byte ASCII serial number while in network-setup mode.
The frame is identified by company ID 0x06A8 (Midea) and usually the
local name "net".
"""

import hashlib

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import register_parser

MIDEA_COMPANY_ID = 0x06A8
FRAME_TYPE_SERIAL = 0x01
SERIAL_LEN = 14
FAMILY_CODE_OFFSET = 5
SUBFRAME_MAC_MARKER = 0x01
BD_ADDR_LEN = 6


@register_parser(
    name="midea_appliance",
    company_id=MIDEA_COMPANY_ID,
    description="GD Midea smart appliance advertisements",
    version="1.0.0",
    core=False,
)
class MideaApplianceParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if raw.company_id != MIDEA_COMPANY_ID:
            return None

        payload = raw.manufacturer_payload
        if payload is None or len(payload) < 1 + SERIAL_LEN:
            return None
        if payload[0] != FRAME_TYPE_SERIAL:
            return None

        serial_bytes = payload[1 : 1 + SERIAL_LEN]
        try:
            serial = serial_bytes.decode("ascii")
        except UnicodeDecodeError:
            return None
        if not all(32 <= b < 127 for b in serial_bytes):
            return None

        metadata: dict = {
            "serial_number": serial,
            "family_code": serial[FAMILY_CODE_OFFSET] if len(serial) > FAMILY_CODE_OFFSET else "",
            "setup_mode": raw.local_name == "net",
        }

        ext_offset = 1 + SERIAL_LEN
        if (
            len(payload) >= ext_offset + 1 + BD_ADDR_LEN
            and payload[ext_offset] == SUBFRAME_MAC_MARKER
        ):
            bd = payload[ext_offset + 1 : ext_offset + 1 + BD_ADDR_LEN]
            metadata["embedded_bd_addr"] = ":".join(f"{b:02X}" for b in bd)

        id_hash = hashlib.sha256(
            f"midea_appliance:{serial}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="midea_appliance",
            beacon_type="midea_appliance",
            device_class="appliance",
            identifier_hash=id_hash,
            raw_payload_hex=raw.manufacturer_data.hex() if raw.manufacturer_data else "",
            metadata=metadata,
        )
