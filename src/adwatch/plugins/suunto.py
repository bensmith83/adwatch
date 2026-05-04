"""Suunto wearable plugin (Race / Vertical / 9 Peak Pro / 7 / 9).

Per apk-ble-hunting/reports/suunto-android_passive.md. Two protocol
generations distinguish Suunto watches:

  - **NG** (newer: Race / Vertical / 9 Peak Pro): service UUID
    ``61353090-8231-49CC-B57A-886370740041``
  - **NSP** (legacy: Suunto 7 / 9 family): service UUID
    ``98AE7120-E62E-11E3-BADD-0002A5D5C51B``

Plus name prefix ``^Suunto ``. SIG Heart Rate `0x180D` is intentionally
NOT matched here (vendor-agnostic, would steal sightings from any HR
strap).
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


SUUNTO_NG_UUID = "61353090-8231-49cc-b57a-886370740041"
SUUNTO_NSP_UUID = "98ae7120-e62e-11e3-badd-0002a5d5c51b"


@register_parser(
    name="suunto",
    service_uuid=[SUUNTO_NG_UUID, SUUNTO_NSP_UUID],
    local_name_pattern=r"^Suunto ",
    description="Suunto watches (NG: Race/Vertical/9 Peak Pro; NSP: Suunto 7/9)",
    version="1.0.0",
    core=False,
)
class SuuntoParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        ng_hit = SUUNTO_NG_UUID in normalized
        nsp_hit = SUUNTO_NSP_UUID in normalized
        local_name = raw.local_name or ""
        name_hit = local_name.startswith("Suunto ")

        if not (ng_hit or nsp_hit or name_hit):
            return None

        metadata: dict = {"vendor": "Suunto"}
        if ng_hit:
            metadata["protocol"] = "ng"
        elif nsp_hit:
            metadata["protocol"] = "nsp"

        if local_name:
            metadata["device_name"] = local_name

        id_basis = f"suunto:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="suunto",
            beacon_type="suunto",
            device_class="wearable",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
