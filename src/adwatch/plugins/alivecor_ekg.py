"""AliveCor Kardia EKG BLE plugin.

Per apk-ble-hunting/reports/alivecor-kardia_passive.md: the modern Kardia
products advertise per-product service UUIDs and a recognizable
device-name prefix:

  - **KardiaMobile 6L** — service UUID
    ``AC060001-328C-A28F-9846-5A8AA212661B`` + name ``KardiaMobile_6L_*``
  - **KardiaCard** — service UUID
    ``AC010001-328C-A28F-9846-5A8AA212661B`` + name ``KardiaCard_*``
  - Legacy detection-only: ``^EKG-`` name prefix (older KardiaMobile
    generations the original plugin targeted) plus a placeholder UUID.

Service-UUID-only detection is a PHI-by-inference channel — the UUID
reveals the user has an FDA-cleared 6-lead ECG device, which is sensitive
even without reading the waveform.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

# Legacy placeholder UUID kept for backwards compatibility with installs
# that adopted the v1.0.0 plugin before the report-driven fix; the modern
# Kardia UUIDs below are the canonical signals.
ALIVECOR_SERVICE_UUID = "021a9004-0382-4aea-bff4-6b3f1c5adfb4"

KARDIA_6L_UUID = "ac060001-328c-a28f-9846-5a8aa212661b"
KARDIACARD_UUID = "ac010001-328c-a28f-9846-5a8aa212661b"

_NAME_RE = re.compile(r"^(KardiaMobile_6L|KardiaCard|KardiaMobile|EKG)[-_](.+)$")
_BARE_NAME_RE = re.compile(r"^(KardiaMobile_6L|KardiaCard|KardiaMobile|EKG)[-_]?$")


@register_parser(
    name="alivecor_ekg",
    service_uuid=[ALIVECOR_SERVICE_UUID, KARDIA_6L_UUID, KARDIACARD_UUID],
    local_name_pattern=r"^(KardiaMobile|KardiaCard|EKG-)",
    description="AliveCor Kardia ECG (Mobile / 6L / Card)",
    version="1.1.0",
    core=False,
)
class AliveCorEkgParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        local_name = getattr(raw, "local_name", None)
        normalized = [u.lower() for u in (raw.service_uuids or [])]

        is_6l = KARDIA_6L_UUID in normalized
        is_card = KARDIACARD_UUID in normalized
        is_legacy_uuid = ALIVECOR_SERVICE_UUID in normalized

        name_match = _NAME_RE.match(local_name or "")
        bare_match = _BARE_NAME_RE.match(local_name or "")
        legacy_ekg = local_name and local_name.startswith("EKG-")

        if not (is_6l or is_card or is_legacy_uuid or name_match or bare_match
                or legacy_ekg):
            return None

        metadata: dict = {}
        if local_name:
            metadata["local_name"] = local_name

        product_family: str | None = None
        if is_6l:
            product_family = "KardiaMobile 6L"
        elif is_card:
            product_family = "KardiaCard"
        elif name_match:
            tag = name_match.group(1)
            product_family = {
                "KardiaMobile_6L": "KardiaMobile 6L",
                "KardiaCard": "KardiaCard",
                "KardiaMobile": "KardiaMobile",
                "EKG": "KardiaMobile (legacy)",
            }.get(tag, tag)

        if product_family:
            metadata["product_family"] = product_family

        device_id: str | None = None
        if name_match:
            device_id = name_match.group(2)
            metadata["device_id"] = device_id
        elif legacy_ekg and not name_match:
            # "EKG-" with no suffix: surface empty string for backwards
            # compatibility with the v1.0.0 plugin.
            suffix = local_name[4:] if local_name else ""
            metadata["device_id"] = suffix
            if suffix:
                device_id = suffix

        if device_id:
            id_basis = f"alivecor_ekg:{device_id}"
        else:
            id_basis = f"{raw.mac_address}:alivecor_ekg"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        raw_hex = raw.manufacturer_data.hex() if raw.manufacturer_data else ""

        return ParseResult(
            parser_name="alivecor_ekg",
            beacon_type="alivecor_ekg",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )

    def storage_schema(self):
        return None
