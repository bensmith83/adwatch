"""Shelly BLU / gen2-gen3 manufacturer-data BLE advertisement plugin.

Per apk-ble-hunting shelly-smartcontrol report (``BleDevice.parseManufacturerData``,
``BleDevice.java:973-1034``), company 0x0BA9 (Allterco Robotics) manufacturer
data is a BTHome-style TLV block, NOT sensor telemetry. Report offsets index
the full mfr data (CID at 0-1), so payload = report offset - 2:

    payload[0] == 0x01 -> flags uint16 LE at payload[1:3] (optional block)
    then TLV objects: 0x0B model id (2, LE) | 0x0A device MAC (6, reversed)
                      | 0x09 JTI (6, hex)

Flags: bit0 discoverable, bit1 auth-enabled, bit2 RPC-enabled, bit3 buzzer,
bit4 pairing-mode, bit5 provision-locked.

BLU sensor telemetry (button/door/motion/temp...) rides in BTHome v2 service
data (UUID 0xFCD2) and is decoded by ``bthome.py``; this plugin deliberately
does not register 0xFCD2. It only surfaces the BTHome encryption bit, since
bthome.py drops encrypted frames.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser, _normalize_uuid

SHELLY_COMPANY_ID = 0x0BA9
_BTHOME_UUID = _normalize_uuid("fcd2")

_MODEL_MAP = {
    "SBBT": "BLU Button",
    "SBDW": "BLU Door/Window",
    "SBMO": "BLU Motion",
    "SBHT": "BLU H&T",
}

_FLAG_BITS = (
    "discoverable",
    "auth_enabled",
    "rpc_enabled",
    "buzzer_enabled",
    "pairing_mode",
    "provision_locked",
)

# TLV object id -> length
_TLV_LEN = {0x0B: 2, 0x0A: 6, 0x09: 6}


def _decode_payload(payload: bytes) -> dict:
    md: dict = {}
    pos = 0
    if len(payload) >= 3 and payload[0] == 0x01:
        flags = int.from_bytes(payload[1:3], "little")
        md["flags"] = flags
        for bit, name in enumerate(_FLAG_BITS):
            md[name] = bool(flags & (1 << bit))
        pos = 3
    while pos < len(payload):
        obj = payload[pos]
        ln = _TLV_LEN.get(obj)
        if ln is None or pos + 1 + ln > len(payload):
            break
        val = payload[pos + 1:pos + 1 + ln]
        pos += 1 + ln
        if obj == 0x0B:
            md["model_id"] = int.from_bytes(val, "little")
        elif obj == 0x0A:
            md["device_mac"] = ":".join(f"{b:02X}" for b in reversed(val))
        elif obj == 0x09:
            md["jti"] = val.hex()
    return md


@register_parser(
    name="shelly_blu",
    company_id=SHELLY_COMPANY_ID,
    local_name_pattern=r"^SB[A-Z]{2}-",
    description="Shelly BLU / gen2-3 manufacturer-data advertisements",
    version="2.0.0",
    core=False,
)
class ShellyBluParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if raw.company_id != SHELLY_COMPANY_ID:
            return None
        payload = raw.manufacturer_payload
        if not payload:
            return None

        local_name = raw.local_name
        is_blu = bool(local_name and local_name.startswith("SB") and len(local_name) >= 4)
        if is_blu:
            model = _MODEL_MAP.get(local_name[:4], "BLU Unknown")
        else:
            model = "Unknown"

        metadata: dict = {"model": model, "local_name": local_name}
        metadata.update(_decode_payload(payload))

        if raw.service_data:
            for key, data in raw.service_data.items():
                if _normalize_uuid(key) == _BTHOME_UUID and data:
                    metadata["bthome_encrypted"] = bool(data[0] & 0x01)
                    break

        if "device_mac" in metadata:
            id_hash = hashlib.sha256(f"shelly:{metadata['device_mac']}".encode()).hexdigest()[:16]
        else:
            id_hash = hashlib.sha256(f"{raw.mac_address}:shelly_blu".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="shelly_blu",
            beacon_type="shelly_blu",
            device_class="sensor" if is_blu else "smart_home",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
