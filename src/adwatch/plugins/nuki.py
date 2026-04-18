"""Nuki Smart Lock BLE advertisement parser.

Per apk-ble-hunting/reports/nuki_passive.md: Nuki uses service-data filtering
with product-family-specific 128-bit UUIDs sharing the suffix
`-5501-11e4-916c-0800200c9a66`. First 4 hex chars of the UUID encode the
product family (A92E lock / A92F bridge / A92B fob / A92D box / A92C keypad);
next 2 chars encode role (00 adv / 01 pairing / 02 user / EF firmware-update).
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import _normalize_uuid, register_parser


NUKI_UUID_SUFFIX = "-5501-11e4-916c-0800200c9a66"

# (uuid, family, role)
NUKI_UUIDS = (
    (f"a92ee000{NUKI_UUID_SUFFIX}", "lock",    "advertising"),
    (f"a92ee100{NUKI_UUID_SUFFIX}", "lock",    "pairing"),
    (f"a92ee200{NUKI_UUID_SUFFIX}", "lock",    "keyturner"),
    (f"a92eef00{NUKI_UUID_SUFFIX}", "lock",    "firmware_update"),
    (f"a92fe000{NUKI_UUID_SUFFIX}", "bridge",  "advertising"),
    (f"a92be000{NUKI_UUID_SUFFIX}", "fob",     "pairing"),
    (f"a92be100{NUKI_UUID_SUFFIX}", "fob",     "user"),
    (f"a92de000{NUKI_UUID_SUFFIX}", "box",     "advertising"),
    (f"a92ce000{NUKI_UUID_SUFFIX}", "keypad",  "advertising"),
)

_UUID_INFO = {_normalize_uuid(u): (family, role) for u, family, role in NUKI_UUIDS}
_ALL_UUIDS = [u for u, _, _ in NUKI_UUIDS]

_FAMILY_DEVICE_CLASS = {
    "lock":   "lock",
    "bridge": "bridge",
    "fob":    "key",
    "box":    "lock",
    "keypad": "keypad",
}


@register_parser(
    name="nuki",
    service_uuid=_ALL_UUIDS,
    description="Nuki smart locks, bridges, fobs, boxes, keypads",
    version="1.0.0",
    core=False,
)
class NukiParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        matched_family = None
        matched_role = None
        matched_uuid = None
        service_payload_hex = None

        for u in (raw.service_uuids or []):
            info = _UUID_INFO.get(_normalize_uuid(u))
            if info:
                matched_family, matched_role = info
                matched_uuid = u.lower()
                break

        if raw.service_data:
            for u, payload in raw.service_data.items():
                info = _UUID_INFO.get(_normalize_uuid(u))
                if info:
                    matched_family, matched_role = info
                    matched_uuid = u.lower()
                    if payload:
                        service_payload_hex = payload.hex()
                    break

        if matched_family is None:
            return None

        roles_in_ad = set()
        for u in (raw.service_uuids or []):
            info = _UUID_INFO.get(_normalize_uuid(u))
            if info:
                roles_in_ad.add(info[1])
        in_pairing_mode = "pairing" in roles_in_ad
        in_firmware_update = "firmware_update" in roles_in_ad

        metadata: dict = {
            "product_family": matched_family,
            "role": matched_role,
            "matched_uuid": matched_uuid,
        }
        if in_pairing_mode:
            metadata["in_pairing_mode"] = True
        if in_firmware_update:
            metadata["in_firmware_update"] = True
        if service_payload_hex:
            metadata["service_payload_hex"] = service_payload_hex

        id_hash = hashlib.sha256(f"nuki:{raw.mac_address}".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="nuki",
            beacon_type="nuki",
            device_class=_FAMILY_DEVICE_CLASS.get(matched_family, "lock"),
            identifier_hash=id_hash,
            raw_payload_hex=service_payload_hex or "",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
