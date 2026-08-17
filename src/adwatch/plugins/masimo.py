"""Masimo BLE advertisement parser (MightySat pulse oximeter + Stork family).

Per apk-ble-hunting/reports/masimo-merlin-consumer_passive.md and
apk-ble-hunting/reports/masimo-stork_passive.md.

Masimo's apps discover devices with `setManufacturerData(579, null)` — i.e.
company ID 0x0243 *presence* only, with no byte pattern — optionally combined
with a per-module Stork service UUID:

  - STK sensor    913E1000-599E-4F9C-86B3-4B1CA8D24A30
  - Stork sensor  76C01000-3C37-42DC-B66F-888DEA4DCA72
  - Stork hub / camera: company ID only, no distinguishing service UUID.

No advertisement bytes are decoded by either app (zero
`getManufacturerSpecificData` call sites), so the passive leak is presence +
vendor + (via service UUID) device type. All SpO2/pulse/temperature telemetry
is GATT-only, post-bonding.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


MASIMO_COMPANY_ID = 0x0243

# Stork per-module service UUIDs used as scan filters (ModuleID.java:421,481).
STORK_STK_SERVICE_UUID = "913e1000-599e-4f9c-86b3-4b1ca8d24a30"
STORK_SENSOR_SERVICE_UUID = "76c01000-3c37-42dc-b66f-888dea4dca72"

STORK_MODULES = {
    STORK_STK_SERVICE_UUID: "STK",
    STORK_SENSOR_SERVICE_UUID: "STORK_SENSOR",
}
STORK_SERVICE_UUIDS = tuple(STORK_MODULES)

def _stork_module(raw: RawAdvertisement) -> str | None:
    """Return the Stork module name if a Stork service UUID is advertised."""
    for advertised in (raw.service_uuids or []):
        module = STORK_MODULES.get(advertised.lower())
        if module:
            return module
    for key in (raw.service_data or {}):
        module = STORK_MODULES.get(key.lower())
        if module:
            return module
    return None


@register_parser(
    name="masimo",
    company_id=MASIMO_COMPANY_ID,
    service_uuid=list(STORK_SERVICE_UUIDS),
    local_name_pattern=r"(?i)^(MightySat|Masimo)",
    description="Masimo MightySat pulse oximeter / Stork infant monitor",
    version="1.1.0",
    core=False,
)
class MasimoParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        has_company = (
            raw.manufacturer_data
            and len(raw.manufacturer_data) >= 2
            and int.from_bytes(raw.manufacturer_data[:2], "little") == MASIMO_COMPANY_ID
        )
        name = raw.local_name or ""
        name_match = name.lower().startswith(("mightysat", "masimo"))
        module = _stork_module(raw)

        if not (has_company or name_match or module):
            return None

        metadata: dict = {}
        if has_company:
            metadata["cid_match"] = True
        if name:
            metadata["device_name"] = name
        if module:
            # Stork infant SpO2/pulse/temperature monitor — the service UUID is
            # the only device-type discriminator; hub/camera advertise the CID
            # alone and are indistinguishable passively.
            metadata["product_family"] = "stork"
            metadata["stork_module"] = module
        payload = raw.manufacturer_payload
        if payload:
            metadata["protocol_version"] = payload[0]
            metadata["payload_hex"] = payload.hex()

        id_hash = hashlib.sha256(f"masimo:{raw.mac_address}".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="masimo",
            beacon_type="masimo",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex=(payload or b"").hex(),
            metadata=metadata,
        )
