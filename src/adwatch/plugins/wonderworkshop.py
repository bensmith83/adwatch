"""Wonder Workshop Dash / Cue / Dot educational robot plugin.

Per apk-ble-hunting/reports/makewonder-blockly_passive.md. Two service
UUIDs distinguish the robot family:

  - **Dash**: ``AF237777-879D-6186-1F49-DECA0E85D9C1``
  - **Cue / Dot**: ``AF237778-879D-6186-1F49-DECA0E85D9C1``

Local-name format: ``Dash 0123`` / ``Cue 0123`` / ``Dot 0123`` where the
4-char suffix is a stable per-device serial / personality ID.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


DASH_UUID = "af237777-879d-6186-1f49-deca0e85d9c1"
CUE_DOT_UUID = "af237778-879d-6186-1f49-deca0e85d9c1"


@register_parser(
    name="wonderworkshop",
    service_uuid=[DASH_UUID, CUE_DOT_UUID],
    description="Wonder Workshop Dash / Cue / Dot educational robots",
    version="1.0.0",
    core=False,
)
class WonderWorkshopParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        dash_hit = DASH_UUID in normalized
        cue_dot_hit = CUE_DOT_UUID in normalized

        if not (dash_hit or cue_dot_hit):
            return None

        metadata: dict = {"vendor": "Wonder Workshop"}
        if dash_hit:
            metadata["robot"] = "Dash"
        elif cue_dot_hit:
            metadata["robot"] = "Cue/Dot"

        if raw.local_name:
            metadata["device_name"] = raw.local_name

        id_basis = f"wonderworkshop:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="wonderworkshop",
            beacon_type="wonderworkshop",
            device_class="robot_toy",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
