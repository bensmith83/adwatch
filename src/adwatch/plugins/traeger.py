"""Traeger Grills BLE advertisement parser.

Per apk-ble-hunting/reports/traegergrills-app_passive.md. Grills advertise only
during WiFi provisioning — post-setup they go silent. Name prefix `Yosemite`
(Traeger internal codename). Model code is embedded in raw scan-record bytes
via a hack (null-byte→`|`, high-bit-bytes→`,`, CSV-split, index 1) — we don't
have the raw scan record in `RawAdvertisement` so that decode is deferred.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


TRAEGER_NAME_PREFIX = "Yosemite"
TRAEGER_PROVISIONING_SERVICE_UUID = "a8220000-d94e-4a55-9510-a022d3206b8e"

MODEL_CODES = {
    2201: "Model 4 XL",
    2202: "Model 4",
    2203: "Ironwood XL Cabinet",
    2204: "Ironwood Cabinet",
    2205: "Ironwood XL Legs",
    2206: "Ironwood Legs",
}


@register_parser(
    name="traeger",
    service_uuid=TRAEGER_PROVISIONING_SERVICE_UUID,
    local_name_pattern=r"^Yosemite",
    description="Traeger grill provisioning advertisements",
    version="1.0.0",
    core=False,
)
class TraegerParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        name = raw.local_name or ""
        has_name = name.startswith(TRAEGER_NAME_PREFIX)
        has_uuid = TRAEGER_PROVISIONING_SERVICE_UUID in [
            u.lower() for u in (raw.service_uuids or [])
        ]

        if not (has_name or has_uuid):
            return None

        metadata: dict = {"provisioning_mode": True}
        if name:
            metadata["device_name"] = name

        id_hash = hashlib.sha256(
            f"traeger:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="traeger",
            beacon_type="traeger",
            device_class="appliance",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
