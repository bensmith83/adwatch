"""Tractive pet GPS tracker BLE advertisement parser.

Per apk-ble-hunting/reports/tractive-android-gps_passive.md. Four service UUIDs
identify hardware family (Cat/Dog/V2/Fw4); in DFU mode the tracker instead
advertises one of 12 fixed model-code device names.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import _normalize_uuid, register_parser


SERVICE_UUID_CAT = "73180001-1209-416b-8695-777a4eef2568"
SERVICE_UUID_DOG = "c1670001-2c5d-42fd-be9b-1f2dd6681818"
SERVICE_UUID_V2  = "69af0002-f994-3a57-749b-0e0aad3fca18"
SERVICE_UUID_FW4 = "20130001-0719-4b6e-be5d-158ab92fa5a4"

_VARIANT_BY_UUID = {
    _normalize_uuid(SERVICE_UUID_CAT): "Cat",
    _normalize_uuid(SERVICE_UUID_DOG): "Dog",
    _normalize_uuid(SERVICE_UUID_V2):  "V2",
    _normalize_uuid(SERVICE_UUID_FW4): "Fw4",
}

DFU_NAMES = (
    "TRDOG1", "TRCAT1", "TRNJA4",
    "TG4410", "TG4XL", "TG4422", "TG5",
    "TG6A", "TG6C", "TG6D", "TG6XLC", "TG7A",
)


@register_parser(
    name="tractive",
    service_uuid=[SERVICE_UUID_CAT, SERVICE_UUID_DOG, SERVICE_UUID_V2, SERVICE_UUID_FW4],
    local_name_pattern=r"^(?:" + "|".join(DFU_NAMES) + r")$",
    description="Tractive pet GPS tracker (Cat/Dog/V2/Fw4)",
    version="1.0.0",
    core=False,
)
class TractiveParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        variant = None
        for u in (raw.service_uuids or []):
            v = _VARIANT_BY_UUID.get(_normalize_uuid(u))
            if v:
                variant = v
                break

        name = raw.local_name or ""
        dfu_active = name in DFU_NAMES

        if not variant and not dfu_active:
            return None

        metadata: dict = {}
        if variant:
            metadata["family"] = variant
        if dfu_active:
            metadata["dfu_active"] = True
            metadata["dfu_model_code"] = name

        id_hash = hashlib.sha256(
            f"tractive:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="tractive",
            beacon_type="tractive",
            device_class="pet_tracker",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
