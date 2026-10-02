"""Willow Go / Willow 3.0 / 360 wearable breast pump presence plugin.

Per apk-ble-hunting/reports/willow-go_passive.md (+ willow-go_native.md).

Discovery is purely by advertised local-name prefix (hard literals in the
Dart snapshot, though remote-config overridable):
  - ``^WillowGo-`` → Willow Go
  - ``^Willow-``   → Willow 3.0 / 360 (legacy shared prefix)

The pump also advertises a manufacturer-data element the app validates, but
its company ID and layout are not recoverable statically — the raw bytes and
the leading 2-byte (assumed LE CID) are recorded for later live analysis,
never decoded. All session telemetry is behind an encrypted GATT link.

Identity = MAC + name suffix (per report). Flagged ``sensitive=True``:
presence/timing of a breast pump reveals a nursing parent's schedule.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


WILLOW_NAME_PATTERN = r"^Willow(Go)?-"
_NAME_RE = re.compile(r"^Willow(Go)?-(.*)$")


@register_parser(
    name="willow_pump",
    local_name_pattern=WILLOW_NAME_PATTERN,
    description="Willow wearable breast pump (presence-only, name prefix)",
    version="1.0.0",
    core=False,
)
class WillowPumpParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        m = _NAME_RE.match(raw.local_name or "")
        if not m:
            return None

        suffix = m.group(2)
        metadata: dict = {
            "vendor": "Willow",
            "product": "Willow breast pump",
            "generation": "Go" if m.group(1) else "3.0/360",
            "device_name": raw.local_name,
            "name_suffix": suffix,
            "telemetry": "none (encrypted GATT only)",
            "sensitive": True,
            "sensitive_category": "maternal_health",
        }
        mfr = raw.manufacturer_data
        if mfr:
            metadata["mfr_data_hex"] = mfr.hex()
            if raw.company_id is not None:
                metadata["mfr_company_id"] = raw.company_id

        id_hash = hashlib.sha256(
            f"willow_pump:{raw.mac_address}:{suffix}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="willow_pump",
            beacon_type="willow_pump",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex=(mfr or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
