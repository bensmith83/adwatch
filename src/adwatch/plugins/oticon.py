"""Oticon hearing-aid plugin (best-effort heuristic).

Per apk-ble-hunting/reports/oticon-app_passive.md: Oticon Companion is .NET
NativeAOT-compiled and no UUID literals are recoverable from static analysis.
This plugin uses publicly-known signals:

  - Google ASHA service UUID `0xFDF0` (Audio Streaming for Hearing Aids).
  - Name prefix `^Oticon ` (Oticon's own product naming convention).

Both signals together are the high-confidence match. ASHA alone catches all
ASHA-compliant hearing aids (Oticon Real/More/Play, plus other vendors).
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


ASHA_SERVICE_UUID = "fdf0"
DEMANT_COMPANY_ID = 0x01D7  # Demant A/S — Oticon parent

_OTICON_NAME_RE = re.compile(r"^Oticon\s+(\S+)\s*([LRlr])?$")


@register_parser(
    name="oticon",
    company_id=DEMANT_COMPANY_ID,
    service_uuid=ASHA_SERVICE_UUID,
    local_name_pattern=r"^Oticon ",
    description="Oticon hearing aids (ASHA + name heuristic)",
    version="1.0.0",
    core=False,
)
class OticonParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        asha_hit = ASHA_SERVICE_UUID in normalized
        cid_hit = raw.company_id == DEMANT_COMPANY_ID
        name_match = _OTICON_NAME_RE.match(raw.local_name) if raw.local_name else None

        if not (asha_hit or cid_hit or name_match):
            return None

        # ASHA alone matches non-Oticon aids too — only tag as Oticon if name
        # confirms or Demant CID is present.
        is_confirmed_oticon = bool(name_match) or cid_hit
        if asha_hit and not is_confirmed_oticon:
            # Generic ASHA hit — return a presence record but mark uncertain.
            return ParseResult(
                parser_name="oticon",
                beacon_type="oticon",
                device_class="hearing_aid",
                identifier_hash=hashlib.sha256(
                    f"asha:{raw.mac_address}".encode()
                ).hexdigest()[:16],
                raw_payload_hex="",
                metadata={"asha_compliant": True, "vendor_attribution": "uncertain"},
            )

        metadata: dict = {"asha_compliant": asha_hit, "vendor_attribution": "oticon"}
        if name_match:
            metadata["device_name"] = raw.local_name
            metadata["model"] = name_match.group(1)
            if name_match.group(2):
                metadata["side"] = name_match.group(2).upper()

        id_hash = hashlib.sha256(f"oticon:{raw.mac_address}".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="oticon",
            beacon_type="oticon",
            device_class="hearing_aid",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
