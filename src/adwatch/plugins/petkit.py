"""Petkit pet-gadget BLE advertisement plugin.

Per apk-ble-hunting/reports/petkit-oversea_passive.md. Petkit's Android app
(`com.petkit.oversea`) scans unfiltered and post-filters every result with
`checkDeviceFilter()`, a **case-insensitive equality** test against seven
literal local-name strings (`BLEConsts.DeviceFilter`):

    PETKIT, PETKIT2, Fit P1, Fit P2, pethome, petmate, petGO

Per-product differentiation is entirely by that name — every Petkit BLE
product shares the same `0000aaa0-/aaa1-/aaa2-` SIG-base-squat GATT service,
and no manufacturer data or service data is parsed.  Because `0000aaa0` is a
squatted SIG-base UUID that other OEMs also use, it is treated only as a
*confirming* signal here; the name is the authoritative match.

Privacy note from the report: the name is identical across all units of a
SKU (unusually privacy-positive), so the MAC is the only per-unit
discriminator and therefore the identity-hash basis.
"""

import hashlib

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import _normalize_uuid, register_parser


# Shared across the whole Petkit BLE catalogue (aaa1 = DATA, aaa2 = CONTROL).
PETKIT_SERVICE_UUID = "0000aaa0-0000-1000-8000-00805f9b34fb"
_PETKIT_SERVICE_NORM = _normalize_uuid(PETKIT_SERVICE_UUID)

# lowercase advertised name -> product line
PETKIT_MODELS = {
    "petkit": "Fit P1",
    "fit p1": "Fit P1",
    "petkit2": "Fit P2",
    "fit p2": "Fit P2",
    "pethome": "PetHome",
    "petmate": "PetMate",
    "petgo": "petGO",
}

# equalsIgnoreCase in the app -> anchored, case-insensitive alternation here.
PETKIT_NAME_PATTERN = (
    r"(?i)^(?:PETKIT2|PETKIT|Fit P1|Fit P2|pethome|petmate|petGO)$"
)


@register_parser(
    name="petkit",
    local_name_pattern=PETKIT_NAME_PATTERN,
    description="Petkit pet collar / tag (Fit P1, Fit P2, PetHome, PetMate, petGO)",
    version="1.0.0",
    core=False,
)
class PetkitParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.local_name:
            return None
        model = PETKIT_MODELS.get(raw.local_name.strip().lower())
        if model is None:
            return None

        has_service = any(
            _normalize_uuid(u) == _PETKIT_SERVICE_NORM
            for u in (raw.service_uuids or [])
        )

        metadata: dict = {
            "vendor": "Petkit",
            "model": model,
            "device_name": raw.local_name,
            "has_petkit_service": has_service,
        }

        id_hash = hashlib.sha256(
            f"petkit:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="petkit",
            beacon_type="petkit",
            device_class="pet_tracker",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
