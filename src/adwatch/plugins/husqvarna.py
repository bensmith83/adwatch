"""Husqvarna Automower BLE advertisement parser.

Per apk-ble-hunting/reports/husqvarna-automowerconnect_passive.md. Rich TLV
manufacturer-data stream exposes serial number + live operational state
(mowing / charging / parked / error / pairing-mode) without connection.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


HUSQVARNA_COMPANY_ID = 0x0426
HUSQVARNA_SERVICE_UUID = "98bd0001-0b0e-421a-84e5-ddbf75dc6de4"

MOWER_STATES = {
    0: "Off",
    1: "WaitForSafetyPin",
    2: "Stopped",
    3: "FatalError",
    4: "PendingStart",
    5: "Paused",
    6: "InOperation",
    7: "Restricted",
    8: "Error",
}

MOWER_ACTIVITIES = {
    0: "None",
    1: "Charging",
    2: "GoingOut",
    3: "Mowing",
    4: "GoingHome",
    5: "Parked",
    6: "StoppedInGarden",
}

DEVICE_GROUPS = {
    0:  "Unknown",
    10: "Mower",
    12: "ChargingStation",
    17: "WaterPumps",
    18: "WaterControls",
    19: "ReferenceStation",
}


def _parse_tlv_stream(data: bytes) -> dict:
    """Walk TLV entries (len, type, value...) per the Husqvarna blelib format.

    Special-case: type 0xFF introduces a nested payload prefixed with a 2-byte
    company ID that must match 0x0426.
    """
    result = {}
    i = 0
    while i < len(data):
        length = data[i]
        if length == 0 or i + length >= len(data) + 1:
            break
        t = data[i + 1] if i + 1 < len(data) else None
        if t is None:
            break
        value = data[i + 2:i + 1 + length]

        if t == 0xFF and len(value) >= 2:
            inner_cid = int.from_bytes(value[:2], "little")
            if inner_cid == HUSQVARNA_COMPANY_ID:
                nested = _parse_tlv_stream(value[2:])
                result.update(nested)
        elif t == 0x04 and len(value) >= 4:
            serial = int.from_bytes(value[:4], "little")
            if serial != 0xFFFFFFFF:
                result["serial_number"] = serial
        elif t == 0x05 and len(value) >= 1:
            result["is_pairable"] = bool(value[0])
            if len(value) >= 3:
                result["state_code"] = value[1]
                result["state"] = MOWER_STATES.get(value[1], f"Unknown_{value[1]}")
                result["activity_code"] = value[2]
                result["activity"] = MOWER_ACTIVITIES.get(value[2], f"Unknown_{value[2]}")
        elif t == 0x06 and len(value) >= 1:
            result["device_group_code"] = value[0]
            result["device_group"] = DEVICE_GROUPS.get(value[0], f"Unknown_{value[0]}")
            if len(value) >= 2:
                result["product_sub_type"] = value[1]
            if len(value) >= 3:
                result["product_variant"] = value[2]
        elif t == 0x03 and len(value) >= 2:
            result["device_status_bytes"] = value[:2].hex()

        i += 1 + length
    return result


@register_parser(
    name="husqvarna",
    company_id=HUSQVARNA_COMPANY_ID,
    service_uuid=HUSQVARNA_SERVICE_UUID,
    description="Husqvarna Automower robotic mowers + accessories",
    version="1.0.0",
    core=False,
)
class HusqvarnaParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        has_company = (
            raw.manufacturer_data
            and len(raw.manufacturer_data) >= 2
            and int.from_bytes(raw.manufacturer_data[:2], "little") == HUSQVARNA_COMPANY_ID
        )
        has_uuid = HUSQVARNA_SERVICE_UUID in [
            u.lower() for u in (raw.service_uuids or [])
        ]

        if not (has_company or has_uuid):
            return None

        metadata: dict = {}
        if has_company:
            payload = raw.manufacturer_payload
            metadata.update(_parse_tlv_stream(payload or b""))

        if metadata.get("serial_number") is not None:
            id_basis = f"husqvarna:{metadata['serial_number']}"
        else:
            id_basis = f"husqvarna:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="husqvarna",
            beacon_type="husqvarna",
            device_class="mower",
            identifier_hash=id_hash,
            raw_payload_hex=raw.manufacturer_payload.hex() if raw.manufacturer_payload else "",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
