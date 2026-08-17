"""Elite HRV CorSense finger HRV sensor plugin (presence only).

Per apk-ble-hunting/reports/elite-hrv_passive.md.

Elite HRV itself is a connect-required app: it scans on the SIG Heart Rate
Service `0x180D` and reads HR/RR only from GATT notifications on `0x2A37`, and
its JS bundle never reads `manufacturerData` / `serviceData` from a scan result.
The one reusable passive discriminator is the device-name classification the app
does perform — `isCorSense(name)` gates the CorSense-specific firmware/battery
reads — so this plugin matches Elite HRV's own CorSense hardware by name.

Deliberately NOT matched:
  - SIG Heart Rate Service `0x180D` (vendor-agnostic — every HR strap advertises
    it); it is recorded as an enrichment only once the name already matched.
  - Polar / Garmin straps that Elite HRV also pairs with — covered by
    `plugins/polar.py` and `plugins/garmin.py`.

No advert payload is documented for the CorSense (open question in the report),
so no byte decode is claimed here.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


CORSENSE_NAME_TOKEN = "corsense"
SIG_HEART_RATE_SERVICE_UUID = "180d"  # never matched alone

_CORSENSE_NAME_RE = re.compile(r"cor[\s_-]?sense", re.IGNORECASE)


@register_parser(
    name="corsense",
    local_name_pattern=r"(?i)cor[\s_-]?sense",
    description="Elite HRV CorSense finger HRV sensor",
    version="1.0.0",
    core=False,
)
class CorSenseParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        name = raw.local_name or ""
        match = _CORSENSE_NAME_RE.search(name)
        if not match:
            return None

        metadata: dict = {
            "vendor": "Elite HRV",
            "model": "CorSense",
            "device_name": name,
        }
        suffix = name[match.end():].strip(" -_:")
        if suffix:
            metadata["name_suffix"] = suffix

        advertised = {u.lower() for u in (raw.service_uuids or [])}
        advertised |= {k.lower() for k in (raw.service_data or {})}
        if SIG_HEART_RATE_SERVICE_UUID in advertised or any(
            u.startswith("0000180d-") for u in advertised
        ):
            metadata["heart_rate_service_advertised"] = True

        # No advertised serial is documented; the name is the only per-unit token.
        id_hash = hashlib.sha256(f"corsense:{name}".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="corsense",
            beacon_type="corsense",
            device_class="wearable",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )
