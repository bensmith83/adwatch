"""Pebblebee tracker plugin (Honey / Finder / R4K Tag families).

Per apk-ble-hunting/reports/pebblebee-app-hive3_passive.md. Three product
generations share this plugin:

  - **Honey** (legacy): exact local name ``PebbleBee`` — no mfr-data, no
    service UUID.
  - **Finder** (Clip / Card / legacy Stone): SIG CID ``0x0B1E`` (2846) +
    SIG service UUID ``0xFCA5``. Mfr-data carries a 1-byte type
    discriminator at offset 0 of the post-CID payload.
  - **R4K Tag / R4K-FM Tag**: SIG CID ``0x09DA`` (2522) + SIG service
    UUID ``0xFCC7``. R4K-FM also co-advertises the Apple Find My
    framework — the FM frame is handled by the existing apple_findmy
    parser, not here.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


PEBBLEBEE_FINDER_CID = 0x0B1E  # 2846
PEBBLEBEE_R4K_CID = 0x09DA      # 2522
FINDER_SERVICE_UUID = "fca5"
R4K_SERVICE_UUID = "fcc7"

_FINDER_FULL_UUID = "0000fca5-0000-1000-8000-00805f9b34fb"
_R4K_FULL_UUID = "0000fcc7-0000-1000-8000-00805f9b34fb"


@register_parser(
    name="pebblebee",
    company_id=[PEBBLEBEE_FINDER_CID, PEBBLEBEE_R4K_CID],
    service_uuid=[FINDER_SERVICE_UUID, R4K_SERVICE_UUID],
    local_name_pattern=r"^PebbleBee$",
    description="Pebblebee tracker tags (Honey / Finder / R4K)",
    version="1.0.0",
    core=False,
)
class PebblebeeParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        cid = raw.company_id
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        finder_uuid_hit = FINDER_SERVICE_UUID in normalized or _FINDER_FULL_UUID in normalized
        r4k_uuid_hit = R4K_SERVICE_UUID in normalized or _R4K_FULL_UUID in normalized
        local_name = raw.local_name or ""
        honey_name_hit = local_name == "PebbleBee"

        if not (cid in (PEBBLEBEE_FINDER_CID, PEBBLEBEE_R4K_CID)
                or finder_uuid_hit or r4k_uuid_hit or honey_name_hit):
            return None

        metadata: dict = {"vendor": "Pebblebee"}

        family: str
        if cid == PEBBLEBEE_FINDER_CID or finder_uuid_hit:
            family = "Finder"
        elif cid == PEBBLEBEE_R4K_CID or r4k_uuid_hit:
            family = "R4K"
        else:
            family = "Honey"
        metadata["product_family"] = family

        if cid in (PEBBLEBEE_FINDER_CID, PEBBLEBEE_R4K_CID):
            payload = raw.manufacturer_payload or b""
            if len(payload) >= 1:
                metadata["type_discriminator"] = payload[0]
            if len(payload) >= 8:
                # Per the report, byte 1+ encodes role + state. Surface
                # raw bytes; the bit-level decode lives in libapp.so.
                metadata["state_bytes_hex"] = payload[1:8].hex()

        if local_name:
            metadata["device_name"] = local_name

        id_basis = f"pebblebee:{family}:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="pebblebee",
            beacon_type="pebblebee",
            device_class="tracker",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
