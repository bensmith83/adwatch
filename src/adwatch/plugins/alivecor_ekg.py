"""AliveCor Kardia ECG BLE plugin (v1.2.0 — Kardia-only).

Per apk-ble-hunting/reports/alivecor-kardia_passive.md: the modern Kardia
products advertise per-product service UUIDs and a recognizable
device-name prefix:

  - **KardiaMobile 6L** — service UUID
    ``AC060001-328C-A28F-9846-5A8AA212661B`` + name ``KardiaMobile_6L_*``
  - **KardiaCard** — service UUID
    ``AC010001-328C-A28F-9846-5A8AA212661B`` + name ``KardiaCard_*``
  - Older KardiaMobile — name ``KardiaMobile[_*]`` (no known UUID)

Service-UUID-only detection is a PHI-by-inference channel — the UUID
reveals the user has an FDA-cleared 6-lead ECG device, which is sensitive
even without reading the waveform.

**Retraction (2026-08-17).** v1.0.0/v1.1.0 of this plugin also matched the
``^EKG-`` local-name prefix and the "legacy" service UUID
``021a9004-0382-4aea-bff4-6b3f1c5adfb4``. Both were a misattribution and
have been removed:

  * ``021a9004-…`` is the Espressif BLE Wi-Fi-provisioning service UUID
    (see ``espressif_prov.py``), not an AliveCor UUID.
  * The only unit ever observed with an ``EKG-`` name (``EKG-99-23-4c``,
    959k+ sightings) advertised exactly that provisioning UUID and nothing
    else. Fellow's smart kettles are ESP32-based and are literally named
    "EKG" (Stagg EKG / EKG+ / EKG Pro, Corvo EKG); the research doc's second
    "EKG" UUID ``7aebf330-…`` is Fellow's aux service UUID from the
    decompiled Fellow app. That family now belongs to ``fellow.py``.
  * No AliveCor hardware advertises ``EKG-`` names.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

KARDIA_6L_UUID = "ac060001-328c-a28f-9846-5a8aa212661b"
KARDIACARD_UUID = "ac010001-328c-a28f-9846-5a8aa212661b"

# Kardia GAP names: product token, optional ``_``/``-`` + serial / suffix.
_NAME_RE = re.compile(r"^(KardiaMobile_6L|KardiaCard|KardiaMobile)(?:[_-](.+))?$")

_PRODUCT_BY_TAG = {
    "KardiaMobile_6L": "KardiaMobile 6L",
    "KardiaCard": "KardiaCard",
    "KardiaMobile": "KardiaMobile",
}


@register_parser(
    name="alivecor_ekg",
    service_uuid=[KARDIA_6L_UUID, KARDIACARD_UUID],
    local_name_pattern=r"^Kardia",
    description="AliveCor Kardia ECG (Mobile / 6L / Card)",
    version="1.2.0",
    core=False,
)
class AliveCorEkgParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        local_name = getattr(raw, "local_name", None)
        normalized = [u.lower() for u in (raw.service_uuids or [])]

        is_6l = KARDIA_6L_UUID in normalized
        is_card = KARDIACARD_UUID in normalized

        product_family: str | None = (
            "KardiaMobile 6L" if is_6l else ("KardiaCard" if is_card else None)
        )
        device_id: str | None = None
        basis: list[str] = []

        if local_name:
            m = _NAME_RE.match(local_name)
            if m is None:
                # A present non-Kardia name is never claimed, even alongside a
                # Kardia UUID (keeps the name-gate safe for telemetry).
                return None
            if product_family is None:
                product_family = _PRODUCT_BY_TAG.get(m.group(1), m.group(1))
            if m.group(2):
                device_id = m.group(2)
            basis.append("name")
        elif not (is_6l or is_card):
            return None

        if is_6l:
            basis.append("kardia_6l_uuid")
        if is_card:
            basis.append("kardia_card_uuid")

        metadata: dict = {"match_basis": "+".join(basis)}
        if local_name:
            metadata["local_name"] = local_name
        if product_family:
            metadata["product_family"] = product_family
        if device_id:
            metadata["device_id"] = device_id

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
