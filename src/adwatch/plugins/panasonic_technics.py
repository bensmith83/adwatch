"""Panasonic Technics audio plugin (EAH-AZ series earbuds).

Per apk-ble-hunting/reports/panasonic-technicsaudioconnect_passive.md.
Manufacturer-data layout (CID 0x003A, Panasonic Corporation; the bytes
below are the *post-CID* payload — i.e. ``manufacturer_payload`` in
adwatch's models):

  - [0..3] vendor header / version flags (opaque)
  - [4]    device model byte (Constants.DeviceModel enum)
  - [5..10] BR/EDR MAC of the earbud (durable identifier — the BR/EDR
            address is leaked into the BLE advert).

Local-name shapes:
  - ``EAH-<MODEL>`` — older Technics earbuds (AZ40, AZ60, AZ70W, A800)
  - ``Technics EAH-<MODEL>`` — newer flagships (AZ80, AZ100)
  - ``LE-EAH-<MODEL>`` — legacy BLE-only advertising variant

Also exposes Airoha SDK service UUIDs (shared across many Airoha-based
audio products — not Panasonic-unique). We keep them as supplementary
matches only.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


PANASONIC_CID = 0x003A  # 58 — Panasonic Corporation

AIROHA_PRIMARY_UUID = "5052494d-2dab-0341-6972-6f6861424c45"
AIROHA_TRSPX_UUID = "49535343-fe7d-4ae5-8fa9-9fafd205e455"

_NAME_RE = re.compile(r"^(LE-)?(Technics )?(EAH-[A-Z0-9]+)")


@register_parser(
    name="panasonic_technics",
    company_id=PANASONIC_CID,
    service_uuid=[AIROHA_PRIMARY_UUID, AIROHA_TRSPX_UUID],
    local_name_pattern=r"^(EAH-|Technics EAH-|LE-EAH-)",
    description="Panasonic Technics earbuds (EAH-AZ series)",
    version="1.0.0",
    core=False,
)
class PanasonicTechnicsParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        cid_hit = raw.company_id == PANASONIC_CID
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        airoha_hit = any(u in (AIROHA_PRIMARY_UUID, AIROHA_TRSPX_UUID) for u in normalized)
        local_name = raw.local_name or ""
        name_match = _NAME_RE.match(local_name)

        if not (cid_hit or airoha_hit or name_match):
            return None

        metadata: dict = {"vendor": "Panasonic", "brand": "Technics"}

        if name_match:
            metadata["model"] = name_match.group(3)
            if name_match.group(2):
                metadata["technics_branded"] = True
            if name_match.group(1):
                metadata["le_only_variant"] = True
            metadata["device_name"] = local_name

        bd_addr: str | None = None
        if cid_hit:
            payload = raw.manufacturer_payload or b""
            if len(payload) >= 5:
                metadata["model_byte"] = payload[4]
            if len(payload) >= 11:
                mac_bytes = payload[5:11]
                bd_addr = ":".join(f"{b:02X}" for b in mac_bytes)
                metadata["bd_addr"] = bd_addr

        if airoha_hit:
            metadata["airoha_chipset"] = True

        if bd_addr:
            id_basis = f"panasonic_technics:{bd_addr}"
        else:
            id_basis = f"panasonic_technics:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="panasonic_technics",
            beacon_type="panasonic_technics",
            device_class="audio",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
