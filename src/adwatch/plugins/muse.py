"""InteraXon Muse EEG headband plugin.

Per apk-ble-hunting/reports/interaxon-muse_passive.md:

  - SIG service UUID 0xFE8D (InteraXon allocation).
  - InteraXon company_id 0x025E.
  - Local name `Muse-XXYY` or `MuseS-XXYY` (last 5 hex of MAC).
  - Mfr-data byte 1 = device-type code: 5/6/7 = MuseS generation,
    otherwise Muse / Muse 2.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


MUSE_SERVICE_UUID = "fe8d"
INTERAXON_COMPANY_ID = 0x025E

MUSES_DEVICE_TYPE_CODES = (0x05, 0x06, 0x07)

_NAME_RE = re.compile(r"^(Muse[Ss]?)-([0-9A-Fa-f]{4,5})$")


@register_parser(
    name="muse",
    company_id=INTERAXON_COMPANY_ID,
    service_uuid=MUSE_SERVICE_UUID,
    local_name_pattern=r"^MuseS?-",
    description="InteraXon Muse EEG headband (Muse / Muse 2 / Muse S)",
    version="1.0.0",
    core=False,
)
class MuseParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        uuid_hit = (
            MUSE_SERVICE_UUID in normalized
            or any(u.endswith("0000fe8d-0000-1000-8000-00805f9b34fb") for u in normalized)
        )
        cid_hit = raw.company_id == INTERAXON_COMPANY_ID
        name_match = _NAME_RE.match(raw.local_name) if raw.local_name else None

        if not (uuid_hit or cid_hit or name_match):
            return None

        metadata: dict = {}

        # Generation from mfr byte 1.
        payload = raw.manufacturer_payload
        if cid_hit and payload and len(payload) >= 2:
            type_code = payload[1]
            metadata["device_type_code"] = type_code
            if type_code in MUSES_DEVICE_TYPE_CODES:
                metadata["generation"] = "MuseS"
            else:
                metadata["generation"] = "Muse_or_Muse2"

        # Generation from name as fallback.
        if "generation" not in metadata and name_match:
            prefix = name_match.group(1)
            metadata["generation"] = "MuseS" if prefix.lower() == "muses" else "Muse_or_Muse2"

        if name_match:
            metadata["mac_suffix"] = name_match.group(2).upper()
            metadata["device_name"] = raw.local_name

        # Identity prefers the persistent MAC-suffix in the name.
        if name_match:
            id_basis = f"muse:{name_match.group(2).upper()}"
        else:
            id_basis = f"muse:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]
        raw_hex = payload.hex() if payload else ""

        return ParseResult(
            parser_name="muse",
            beacon_type="muse",
            device_class="wearable",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )

    def storage_schema(self):
        return None
