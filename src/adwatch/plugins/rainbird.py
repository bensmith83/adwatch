"""Rain Bird irrigation controller BLE advertisement parser.

Per apk-ble-hunting/reports/rainbird-rainbird2_passive.md. Three detection
paths: name contains RAINBIRD (LNK2/RC2), BAT-(BT|PRO)-<zones> pattern
(ESP-BAT-BT), or Solem family service UUIDs.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


SOLEM_UUID_1 = "f4780001-b9fb-4e6a-9b56-d45f8d5a0a9c"  # placeholder shape
SOLEM_UUID_2 = "863a0001-b9fb-4e6a-9b56-d45f8d5a0a9c"

_RB_NAME_RE = re.compile(
    r"(?i)RAINBIRD|^BAT-(?:BT|PRO)-(\d+)I?$"
)

_BAT_NAME_RE = re.compile(r"^BAT-(?:BT|PRO)-(\d+)(I?)$")


@register_parser(
    name="rainbird",
    service_uuid=[SOLEM_UUID_1, SOLEM_UUID_2],
    local_name_pattern=_RB_NAME_RE.pattern,
    description="Rain Bird irrigation controllers (LNK2 / RC2 / ESP-BAT-BT / Solem)",
    version="1.0.0",
    core=False,
)
class RainbirdParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        name = raw.local_name or ""
        has_rainbird_name = "rainbird" in name.lower()
        bat_match = _BAT_NAME_RE.match(name)
        has_solem_uuid = any(
            u.lower() in (SOLEM_UUID_1, SOLEM_UUID_2)
            for u in (raw.service_uuids or [])
        )

        if not (has_rainbird_name or bat_match or has_solem_uuid):
            return None

        metadata: dict = {}
        if name:
            metadata["device_name"] = name

        if has_rainbird_name:
            metadata["product_family"] = "LNK2/RC2"
        elif bat_match:
            metadata["product_family"] = "ESP-BAT"
            zones = int(bat_match.group(1))
            metadata["zone_count"] = zones
            if "PRO" in name:
                metadata["product_variant"] = "BAT-PRO"
            else:
                metadata["product_variant"] = "BAT-BT"
        elif has_solem_uuid:
            metadata["product_family"] = "Solem"
            # Trailing "I" on Solem names indicates install mode.
            if name.endswith("I"):
                metadata["install_mode"] = True

        id_hash = hashlib.sha256(
            f"rainbird:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="rainbird",
            beacon_type="rainbird",
            device_class="irrigation",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
