"""ResMed CPAP / sleep-test BLE plugin.

Per apk-ble-hunting/reports/resmed-myair_passive.md and resmed-airmini_passive.md.

Three product families share this plugin:

  - **AirMini / AirSense 11 / AirCurve 11** — SIG service UUID ``0xFD56``
    (ResMed-assigned). Local name carries the serial: ``AirMini-<serial>``,
    ``AS11-<serial>``, ``AirCurve-<serial>``, or generic ``ResMed <num>``.
  - **NightOwl** home sleep-test — service UUID
    ``4D521000-9E6F-4570-880A-67A5FCB14F12`` + name prefix ``NightOwl``.
  - **POC** portable oxygen concentrator — service UUID
    ``D2009798-1152-4817-9102-3551F72407ED``.

Note: the AirMini *also* runs over BR/EDR (RFCOMM/SPP) — see
resmed-airmini_passive.md. The BLE advertisement is on AirSense 11 /
AirCurve 11 / newer AirMini hardware variants.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

RESMED_COMPANY_ID = 0x038D
RESMED_SERVICE_UUID = "fd56"
NIGHTOWL_SERVICE_UUID = "4d521000-9e6f-4570-880a-67a5fcb14f12"
POC_SERVICE_UUID = "d2009798-1152-4817-9102-3551f72407ed"

# Generic legacy: "ResMed 111682"
RESMED_GENERIC_RE = re.compile(r"^ResMed\s+(\d+)")
# AirMini-family per myAir report: ^(AirMini|AS11|AirCurve)-[A-Z0-9]{10,14}$
AIR_FAMILY_RE = re.compile(r"^(AirMini|AS11|AirCurve)-([A-Z0-9]{10,14})$")
NIGHTOWL_RE = re.compile(r"^NightOwl")


@register_parser(
    name="resmed",
    company_id=RESMED_COMPANY_ID,
    service_uuid=[RESMED_SERVICE_UUID, NIGHTOWL_SERVICE_UUID, POC_SERVICE_UUID],
    local_name_pattern=r"^(ResMed\s|AirMini-|AS11-|AirCurve-|NightOwl)",
    description="ResMed CPAP / NightOwl / POC advertisements",
    version="1.1.0",
    core=False,
)
class ResmedParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]

        fd56_hit = (
            RESMED_SERVICE_UUID in normalized
            or any(u.endswith("0000fd56-0000-1000-8000-00805f9b34fb") for u in normalized)
        )
        nightowl_uuid_hit = NIGHTOWL_SERVICE_UUID in normalized
        poc_uuid_hit = POC_SERVICE_UUID in normalized
        company_match = raw.company_id == RESMED_COMPANY_ID

        local_name = raw.local_name or ""
        generic_match = RESMED_GENERIC_RE.match(local_name)
        air_match = AIR_FAMILY_RE.match(local_name)
        nightowl_name_hit = bool(NIGHTOWL_RE.match(local_name))

        if not (fd56_hit or nightowl_uuid_hit or poc_uuid_hit
                or company_match or generic_match or air_match
                or nightowl_name_hit):
            return None

        metadata: dict = {}
        device_class = "cpap"
        serial: str | None = None

        if air_match:
            family = air_match.group(1)
            serial = air_match.group(2)
            metadata["product_family"] = family
            metadata["serial"] = serial
            metadata["device_name"] = local_name
        elif generic_match:
            metadata["device_number"] = generic_match.group(1)
            metadata["device_name"] = local_name
        elif nightowl_name_hit or nightowl_uuid_hit:
            device_class = "sleep_test"
            metadata["product_family"] = "NightOwl"
            if local_name:
                metadata["device_name"] = local_name
        elif poc_uuid_hit:
            device_class = "oxygen_concentrator"
            metadata["product_family"] = "POC"

        if fd56_hit and "product_family" not in metadata:
            metadata["service_uuid_match"] = "fd56"

        if raw.company_id is not None:
            metadata["company_id"] = f"0x{raw.company_id:04x}"
        if raw.manufacturer_payload:
            metadata["payload_hex"] = raw.manufacturer_payload.hex()

        if serial is not None:
            id_basis = f"resmed:{serial}"
        else:
            id_basis = f"{raw.mac_address}:resmed"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="resmed",
            beacon_type="resmed",
            device_class=device_class,
            identifier_hash=id_hash,
            raw_payload_hex=raw.manufacturer_data.hex() if raw.manufacturer_data else "",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
