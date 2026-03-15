"""iNode Energy Meter BLE plugin — pulse-counting energy monitor."""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

MAGIC_BYTE = 0x82
DEVICE_TYPE_MAP = {
    0x90: "standard",
    0x92: "light_sensor",
    0x94: "dual_tariff",
    0x96: "three_phase",
}


@register_parser(
    name="inode_energy",
    local_name_pattern=r"^iNode",
    description="iNode Energy Meter pulse-counting power monitor",
    version="1.0.0",
    core=False,
)
class INodeEnergyParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 13:
            return None

        data = raw.manufacturer_data

        # Validate magic byte at offset 3
        if data[3] != MAGIC_BYTE:
            return None

        # Device type at offset 0
        device_type_byte = data[0]
        device_type = DEVICE_TYPE_MAP.get(device_type_byte)
        if device_type is None:
            return None

        total_pulses = struct.unpack_from("<I", data, 4)[0]
        average_power = struct.unpack_from("<H", data, 8)[0]
        battery_mv = struct.unpack_from("<H", data, 10)[0]
        battery_pct = data[12]

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:inode_energy".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="inode_energy",
            beacon_type="inode_energy",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata={
                "total_pulses": total_pulses,
                "average_power": average_power,
                "battery_voltage": battery_mv,
                "battery_percent": battery_pct,
                "device_type": device_type,
            },
        )

    def storage_schema(self):
        return None
