"""Chamberlain myQ / Tend / Lockitron plugin.

Per apk-ble-hunting/reports/chamberlain-android-liftmaster-myq_passive.md.
The myQ companion app discovers three heterogeneous device families with
no shared vendor prefix:

  - **Chamberlain Hub (CHUB)** — service UUID
    ``26d91a37-c279-4d0f-96a1-532ce41ce0f6``
  - **Tend Camera** — service UUID ``0x1888`` (SIG-base 16-bit) +
    optional ``Lynx`` local-name prefix
  - **Lockitron (legacy)** — service UUID
    ``A1A51A18-7B77-47D2-91DB-34A48DCD3DE9``

Advertisements carry no telemetry — all state arrives over GATT post
connect. The CHUB is a noteworthy privacy concern: post-connect JSON
traffic is unbonded + cleartext per the report.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


CHUB_UUID = "26d91a37-c279-4d0f-96a1-532ce41ce0f6"
TEND_UUID = "00001888-0000-1000-8000-00805f9b34fb"
LOCKITRON_UUID = "a1a51a18-7b77-47d2-91db-34a48dcd3de9"


@register_parser(
    name="chamberlain_myq",
    service_uuid=[CHUB_UUID, TEND_UUID, LOCKITRON_UUID],
    local_name_pattern=r"^Lynx",
    description="Chamberlain myQ Hub / Tend Camera / Lockitron",
    version="1.0.0",
    core=False,
)
class ChamberlainMyqParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        chub_hit = CHUB_UUID in normalized
        tend_uuid_hit = (
            TEND_UUID in normalized
            or "1888" in normalized
        )
        lockitron_hit = LOCKITRON_UUID in normalized

        local_name = raw.local_name or ""
        lynx_name_hit = local_name.startswith("Lynx")

        if not (chub_hit or tend_uuid_hit or lockitron_hit or lynx_name_hit):
            return None

        metadata: dict = {"vendor": "Chamberlain"}
        device_class: str
        if chub_hit:
            metadata["product_class"] = "garage_hub"
            device_class = "garage_door"
        elif tend_uuid_hit or lynx_name_hit:
            metadata["product_class"] = "tend_camera"
            device_class = "camera"
            metadata["vendor"] = "Tend"
        elif lockitron_hit:
            metadata["product_class"] = "lockitron"
            device_class = "lock"
            metadata["vendor"] = "Lockitron"
            metadata["legacy_product"] = True
        else:
            metadata["product_class"] = "unknown"
            device_class = "unknown"

        if local_name:
            metadata["device_name"] = local_name

        id_basis = f"chamberlain_myq:{metadata['product_class']}:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="chamberlain_myq",
            beacon_type="chamberlain_myq",
            device_class=device_class,
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
