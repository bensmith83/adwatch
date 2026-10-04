"""greenteg CORE core-body-temperature sensor plugin.

Per apk-ble-hunting/reports/greenteg-core-app_passive.md (Leitwert SDK
``BleScanner.parseManufacturerData``). Matching is on the two vendor 128-bit
service UUIDs (application vs bootloader mode). The app does not filter on a
company ID: it takes the first manufacturer-data element and requires value
byte 0 == 0x00. That header is far too weak to claim on, so manufacturer data
is decoded only when one of the UUIDs is present.

Offsets are into the SparseArray value (CID already stripped) -> map directly
onto ``manufacturer_payload[N]``:
  [0]    0x00 header
  [1]    bits0-2 deviceState (index->name mapping unconfirmed), bit5 occupied/worn
  [2:4]  live core temp, LE uint16 milli-degC
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser, _normalize_uuid


GREENTEG_APP_UUID = "00004200-f366-40b2-ac37-70cce0aa83b1"
GREENTEG_BOOTLOADER_UUID = "00002100-5b1e-4347-b07c-97b514dae121"

# Report's suggested sanity band (25-45 degC).
_PLAUSIBLE_MC = (25000, 45000)


@register_parser(
    name="greenteg_core",
    service_uuid=[GREENTEG_APP_UUID, GREENTEG_BOOTLOADER_UUID],
    description="greenteg CORE body-temperature sensor (live core temp broadcast)",
    version="1.0.0",
    core=False,
)
class GreentegCoreParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        uuids = {_normalize_uuid(u) for u in (raw.service_uuids or [])}
        if GREENTEG_APP_UUID in uuids:
            mode = "application"
        elif GREENTEG_BOOTLOADER_UUID in uuids:
            mode = "bootloader"
        else:
            return None

        metadata: dict = {
            "vendor": "greenteg",
            "product": "CORE body temperature sensor",
            "mode": mode,
            "sensitive": True,
            "sensitive_category": "body_temperature",
        }

        payload = raw.manufacturer_payload
        if raw.company_id is not None:
            metadata["company_id"] = raw.company_id
        if payload and len(payload) >= 4 and payload[0] == 0x00:
            flags = payload[1]
            temp_mc = int.from_bytes(payload[2:4], "little")
            metadata["device_state_code"] = flags & 0x07
            metadata["service_occupied"] = bool((flags >> 5) & 1)
            metadata["core_temp_mC"] = temp_mc
            metadata["core_temp_c"] = round(temp_mc / 1000.0, 3)
            metadata["core_temp_plausible"] = _PLAUSIBLE_MC[0] <= temp_mc <= _PLAUSIBLE_MC[1]

        if raw.local_name:
            metadata["device_name"] = raw.local_name

        # No in-payload id; MAC is reported stable (no randomization).
        id_hash = hashlib.sha256(f"greenteg_core:{raw.mac_address}".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="greenteg_core",
            beacon_type="greenteg_core",
            device_class="wearable",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex() if payload else "",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
