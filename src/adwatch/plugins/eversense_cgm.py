"""Senseonics Eversense CGM transmitter plugin.

Per apk-ble-hunting/reports/senseonics-gen12androidapp_passive.md:

  - Custom 128-bit service UUID c3230001-9308-47ae-ac12-3d030892a211.
  - No mfr-data, no service-data, no name prefix used by the app.
  - Identification by service UUID alone.

This is a class-III implanted CGM — observing the UUID is medical-condition
inference (Type-1/Type-2 diabetic with implanted Eversense E3 transmitter).
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


EVERSENSE_SERVICE_UUID = "c3230001-9308-47ae-ac12-3d030892a211"


@register_parser(
    name="eversense_cgm",
    service_uuid=EVERSENSE_SERVICE_UUID,
    description="Senseonics Eversense CGM transmitter",
    version="1.0.0",
    core=False,
)
class EversenseCgmParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        if EVERSENSE_SERVICE_UUID not in normalized:
            return None

        metadata: dict = {"product": "Eversense E3 CGM"}
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
