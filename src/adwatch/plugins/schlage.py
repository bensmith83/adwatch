"""Schlage / Allegion smart lock BLE advertisement parser.

Per apk-ble-hunting/reports/allegion-leopard_passive.md. Multiple device types:
Sense (Leopard), Encode/Encode Plus (WiFi), NDE 358 (Swordfish), Walton,
Selene (Gainsborough). Detection primarily by name pattern + the Sense uWeave
128-bit service UUID.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


# Sense Android-mode / uWeave 128-bit service UUID (little-endian in raw ad).
SENSE_UWEAVE_UUID = "1f6b43aa-94de-4ba9-981c-da38823117bd"

# Name prefixes / substrings per passive report.
_SCHLAGE_NAME_RE = re.compile(
    r"(?:SENSE|schlage|NDE|Walton|GSELENT|SSELENT)", re.IGNORECASE
)


def _extract_encode_serial(name: str) -> str | None:
    """Encode/Encode Plus WiFi locks embed the serial after 'schlage'."""
    low = name.lower()
    if "schlage" in low:
        stripped = low.replace("schlage", "").strip()
        if stripped:
            return stripped
    return None


@register_parser(
    name="schlage",
    service_uuid=SENSE_UWEAVE_UUID,
    local_name_pattern=_SCHLAGE_NAME_RE.pattern,
    description="Schlage / Allegion smart locks",
    version="1.0.0",
    core=False,
)
class SchlageParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        name = raw.local_name or ""
        has_uuid = SENSE_UWEAVE_UUID in [u.lower() for u in (raw.service_uuids or [])]
        name_match = bool(_SCHLAGE_NAME_RE.search(name))

        if not (has_uuid or name_match):
            return None

        metadata: dict = {}
        product = None
        serial = None

        low = name.lower()
        if "sense" in low:
            product = "Sense"
        elif "schlage" in low:
            product = "Encode"
            serial = _extract_encode_serial(name)
        elif "nde" in low:
            product = "NDE 358"
        elif "walton" in low:
            product = "Walton"
        elif "gselent" in low or "sselent" in low:
            product = "Selene"

        if product:
            metadata["product"] = product
        if serial:
            metadata["serial"] = serial
        if has_uuid:
            metadata["has_uweave_service"] = True
        if name:
            metadata["device_name"] = name

        if serial:
            id_basis = f"schlage:{serial}"
        else:
            id_basis = f"schlage:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="schlage",
            beacon_type="schlage",
            device_class="lock",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
