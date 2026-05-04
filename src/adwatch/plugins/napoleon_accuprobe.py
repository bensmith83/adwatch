"""Napoleon ACCU-PROBE BBQ thermometer plugin.

Per apk-ble-hunting/reports/napoleon-accuprobe_passive.md: 16-bit service
UUID ``0xFF00`` plus name substring ``NAP_KT`` (V1) or ``ACCU-PROBE`` (V2).
The 0xFF00 UUID is a commodity-module SIG choice (other vendors use it
too), so UUID-only matches are flagged ``confidence=low``; UUID + name is
``high``.

Advertisements carry no telemetry — temperatures arrive over GATT
notifications post-connect.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


NAPOLEON_SERVICE_UUID = "ff00"
_NAPOLEON_FULL_UUID = "0000ff00-0000-1000-8000-00805f9b34fb"

_V1_RE = re.compile(r"NAP_KT")
_V2_RE = re.compile(r"ACCU-PROBE")


@register_parser(
    name="napoleon_accuprobe",
    service_uuid=NAPOLEON_SERVICE_UUID,
    local_name_pattern=r"(NAP_KT|ACCU-PROBE)",
    description="Napoleon ACCU-PROBE BBQ thermometer",
    version="1.0.0",
    core=False,
)
class NapoleonAccuprobeParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        uuid_hit = NAPOLEON_SERVICE_UUID in normalized or _NAPOLEON_FULL_UUID in normalized

        local_name = raw.local_name or ""
        v1_hit = bool(_V1_RE.search(local_name))
        v2_hit = bool(_V2_RE.search(local_name))
        name_hit = v1_hit or v2_hit

        if not (uuid_hit or name_hit):
            return None

        family: str
        if v1_hit:
            family = "v1"
        elif v2_hit:
            family = "v2"
        else:
            family = "unknown"

        confidence = "high" if (uuid_hit and name_hit) else ("medium" if name_hit else "low")

        metadata: dict = {
            "vendor": "Napoleon",
            "product_family": family,
            "confidence": confidence,
        }
        if local_name:
            metadata["device_name"] = local_name

        id_basis = f"napoleon_accuprobe:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="napoleon_accuprobe",
            beacon_type="napoleon_accuprobe",
            device_class="thermometer",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
