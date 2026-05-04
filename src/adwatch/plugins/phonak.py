"""Phonak / Sonova hearing-aid plugin.

Per apk-ble-hunting/reports/sonova-phonak-dsapp_passive.md:

  - Sonova SIG-assigned company_id 0x0282 (642).
  - Mfr-data byte layout opaque (decoded in libMobileCoreJni.so).
  - Backup signal: name regex ^(Audeo|Audéo|Naída|Virto|Sky|Phonak) .

Hearing aids are PHI-adjacent — the CID alone identifies hearing-loss users.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


SONOVA_COMPANY_ID = 0x0282

_PHONAK_NAME_RE = re.compile(
    r"^(Audeo|Aud[eé]o|Na[ií]da|Virto|Sky|Phonak)\b", re.IGNORECASE
)


@register_parser(
    name="phonak",
    company_id=SONOVA_COMPANY_ID,
    local_name_pattern=r"(?i)^(Audeo|Aud[eé]o|Na[ií]da|Virto|Sky|Phonak)",
    description="Phonak / Sonova hearing aids",
    version="1.0.0",
    core=False,
)
class PhonakParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        cid_hit = raw.company_id == SONOVA_COMPANY_ID
        name_match = _PHONAK_NAME_RE.match(raw.local_name) if raw.local_name else None

        if not (cid_hit or name_match):
            return None

        metadata: dict = {"vendor": "Sonova"}
        if cid_hit:
            metadata["cid_match"] = True
            payload = raw.manufacturer_payload
            if payload:
                metadata["payload_hex"] = payload.hex()
                metadata["payload_length"] = len(payload)
        if name_match:
            metadata["device_name"] = raw.local_name
            metadata["product_line"] = name_match.group(1).lower()

        id_hash = hashlib.sha256(f"phonak:{raw.mac_address}".encode()).hexdigest()[:16]
        raw_hex = raw.manufacturer_data.hex() if raw.manufacturer_data else ""

        return ParseResult(
            parser_name="phonak",
            beacon_type="phonak",
            device_class="hearing_aid",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )

    def storage_schema(self):
        return None
