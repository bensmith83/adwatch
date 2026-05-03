"""Lezyne GPS cycling-computer plugin.

Per apk-ble-hunting/reports/lezyne-gpsally_passive.md. Lezyne head units
(Mega XL, Mega C, Macro Plus, Super Pro, Micro C) advertise the vendor
service UUID ``904D0001-2CE9-078D-944D-263FD93D95B2`` continuously while
powered. Discovery is purely UUID-based — no manufacturer-data or
service-data parsing in the app.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


LEZYNE_SERVICE_UUID = "904d0001-2ce9-078d-944d-263fd93d95b2"


@register_parser(
    name="lezyne",
    service_uuid=LEZYNE_SERVICE_UUID,
    description="Lezyne GPS cycling computer (Mega XL/C, Macro Plus, Super Pro, Micro C)",
    version="1.0.0",
    core=False,
)
class LezyneParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        uuid_hit = LEZYNE_SERVICE_UUID in normalized
        sd_hit = bool(raw.service_data and LEZYNE_SERVICE_UUID in raw.service_data)
        if not (uuid_hit or sd_hit):
            return None

        metadata: dict = {"vendor": "Lezyne"}
        if raw.local_name:
            metadata["device_name"] = raw.local_name
        if sd_hit and raw.service_data:
            metadata["service_data_hex"] = raw.service_data[LEZYNE_SERVICE_UUID].hex()

        id_basis = f"lezyne:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="lezyne",
            beacon_type="lezyne",
            device_class="cycling_computer",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
