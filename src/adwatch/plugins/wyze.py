"""Wyze (Hualai) plugin (Lock family + EarBuds).

Per apk-ble-hunting/reports/wyze-hualai_passive.md. Two product surfaces:

  - **Wyze EarBuds**: SIG-allocated service UUID ``0xFD7B`` (Wyze Labs
    Inc.) — a unique Wyze identifier.
  - **Wyze Lock / Lock Bolt / Lock Keypad / Gunsafe**: advertise SIG
    Battery Service ``0x180F`` (vendor-agnostic — UUID alone is NOT a
    Wyze signal). Discovery requires the name regex
    ``^(Wyze (Lock|Lock Bolt|Lock Keypad|Gunsafe)|DingDing)``. The
    `DingDing` name comes from the Yunding (Lockin/Ford) lock OEM.

Privacy note from the report: ``Wyze Gunsafe`` in the broadcast name is
sensitive (firearm-storage signal). Surfaced as `sensitive=True` so
downstream collectors can scrub before logging.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


WYZE_EARBUDS_UUID = "fd7b"
_WYZE_EARBUDS_FULL = "0000fd7b-0000-1000-8000-00805f9b34fb"
BATTERY_SERVICE_UUID = "0000180f-0000-1000-8000-00805f9b34fb"

_LOCK_RE = re.compile(r"^(Wyze (Lock Bolt|Lock Keypad|Lock|Gunsafe)|DingDing)\b(.*)?")
_VARIANT_PRIORITY = ["Lock Bolt", "Lock Keypad", "Gunsafe", "Lock"]


@register_parser(
    name="wyze",
    service_uuid=WYZE_EARBUDS_UUID,
    local_name_pattern=r"^(Wyze (Lock|Lock Bolt|Lock Keypad|Gunsafe)|DingDing)",
    description="Wyze EarBuds + Wyze Lock family (Lock/Lock Bolt/Keypad/Gunsafe)",
    version="1.0.0",
    core=False,
)
class WyzeParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        earbuds_hit = (
            WYZE_EARBUDS_UUID in normalized
            or _WYZE_EARBUDS_FULL in normalized
        )
        battery_uuid_seen = (
            "180f" in normalized or BATTERY_SERVICE_UUID in normalized
        )

        local_name = raw.local_name or ""
        lock_match = _LOCK_RE.match(local_name)

        if not (earbuds_hit or lock_match):
            return None

        metadata: dict = {"vendor": "Wyze"}
        if local_name:
            metadata["device_name"] = local_name

        if earbuds_hit:
            metadata["product_class"] = "earbuds"
            device_class = "audio"
        elif lock_match:
            metadata["product_class"] = "lock"
            device_class = "lock"
            # Pick the longest matching variant so "Lock Bolt" wins over
            # the substring "Lock".
            for variant in _VARIANT_PRIORITY:
                if local_name.startswith(f"Wyze {variant}"):
                    metadata["product_variant"] = variant
                    if variant == "Gunsafe":
                        metadata["sensitive"] = True
                    break
            else:
                if local_name.startswith("DingDing"):
                    metadata["product_variant"] = "Yunding (DingDing)"
            metadata["confidence"] = "high" if battery_uuid_seen else "medium"
        else:
            metadata["product_class"] = "unknown"
            device_class = "unknown"

        id_basis = f"wyze:{metadata['product_class']}:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="wyze",
            beacon_type="wyze",
            device_class=device_class,
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
