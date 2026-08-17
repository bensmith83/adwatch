"""Senseonics Eversense CGM transmitter plugin.

Per apk-ble-hunting/reports/senseonics-gen12androidapp_passive.md and
apk-ble-hunting/reports/senseonics-eversense365-us_passive.md:

  - Custom 128-bit service UUID c3230001-9308-47ae-ac12-3d030892a211 — the sole
    discovery signal for both the E3 and the Eversense 365 transmitter (both
    apps scan unfiltered and test the parsed AD service-UUID list for it).
  - The 365 report additionally flags the Phx2-variant services c3230002 /
    c3230003 on the same base as worth watching for.
  - No mfr-data, no service-data, no name prefix is used by either app. All
    glucose telemetry is inside the connected Phx2 secure channel.
  - The Nordic DFU base 258eafa5-e914-47da-95ca-c5ab0dc85b11 may appear while
    the transmitter is updating firmware. It is vendor-agnostic, so it is never
    a match criterion — only reported when co-advertised with an Eversense UUID.

This is a class-III implanted CGM — observing the UUID is medical-condition
inference (a diabetic wearing an implanted Eversense transmitter).
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import _normalize_uuid, register_parser


EVERSENSE_SERVICE_UUID = "c3230001-9308-47ae-ac12-3d030892a211"
EVERSENSE_PHX2_UUID_2 = "c3230002-9308-47ae-ac12-3d030892a211"
EVERSENSE_PHX2_UUID_3 = "c3230003-9308-47ae-ac12-3d030892a211"

EVERSENSE_SERVICE_UUIDS = (
    EVERSENSE_SERVICE_UUID,
    EVERSENSE_PHX2_UUID_2,
    EVERSENSE_PHX2_UUID_3,
)

# Nordic DFU (firmware update) base — metadata only, never matched alone.
NORDIC_DFU_UUID = "258eafa5-e914-47da-95ca-c5ab0dc85b11"

_NORMALIZED_TO_UUID = {_normalize_uuid(u): u for u in EVERSENSE_SERVICE_UUIDS}
_DFU_NORMALIZED = _normalize_uuid(NORDIC_DFU_UUID)


@register_parser(
    name="eversense_cgm",
    service_uuid=EVERSENSE_SERVICE_UUIDS,
    description="Senseonics Eversense CGM transmitter (E3 / 365)",
    version="1.1.0",
    core=False,
)
class EversenseCgmParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        advertised = {_normalize_uuid(u) for u in (raw.service_uuids or [])}
        advertised |= {_normalize_uuid(k) for k in (raw.service_data or {})}

        matched = None
        for normalized, uuid in _NORMALIZED_TO_UUID.items():
            if normalized in advertised:
                matched = uuid
                break
        if matched is None:
            return None

        metadata: dict = {
            "product": "Eversense CGM smart transmitter",
            "product_family": "Eversense E3 / 365",
            "matched_service": matched,
        }
        if _DFU_NORMALIZED in advertised:
            metadata["firmware_update_mode"] = True
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        id_hash = hashlib.sha256(f"eversense:{raw.mac_address}".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="eversense_cgm",
            beacon_type="eversense_cgm",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
