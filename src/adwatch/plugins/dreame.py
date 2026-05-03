"""Dreame / Mova robot vacuum & mower plugin.

Dreame products advertise via two paths:

  - Legacy: service UUID ``0xFD92`` + local name ``DL-<serial>``
  - MiIO provisioning (per apk-ble-hunting/reports/dreame-smartlife): the
    Xiaomi MiIO service UUID ``0xFE98`` plus service-data whose UTF-8
    contents start with ``dreame`` or ``mova`` (case-insensitive). The
    MiIO path is a Xiaomi-ecosystem co-branding — `0xFE98` will also see
    other Xiaomi-family devices, so we gate brand detection on the ASCII
    service-data prefix.
"""

import hashlib
import re

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import register_parser

DREAME_SERVICE_UUID = "fd92"
DREAME_SERVICE_UUID_FULL = "0000fd92-0000-1000-8000-00805f9b34fb"
MIIO_SERVICE_UUID = "fe98"
MIIO_SERVICE_UUID_FULL = "0000fe98-0000-1000-8000-00805f9b34fb"

DREAME_NAME_RE = re.compile(r"^DL-(\S+)")


@register_parser(
    name="dreame",
    service_uuid=[DREAME_SERVICE_UUID, MIIO_SERVICE_UUID],
    local_name_pattern=r"^(DL-|dreame|mova)",
    description="Dreame / Mova robot vacuum + mower advertisements",
    version="1.1.0",
    core=False,
)
class DreameParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        legacy_uuid = (
            DREAME_SERVICE_UUID in normalized
            or DREAME_SERVICE_UUID_FULL in normalized
        )
        miio_uuid = (
            MIIO_SERVICE_UUID in normalized
            or MIIO_SERVICE_UUID_FULL in normalized
        )

        local_name = raw.local_name or ""
        name_match = DREAME_NAME_RE.match(local_name)

        # MiIO service-data prefix gating: only claim the device when the
        # ASCII bytes start with dreame/mova.
        miio_brand = None
        miio_payload_str: str | None = None
        if miio_uuid and raw.service_data:
            for k in (MIIO_SERVICE_UUID, MIIO_SERVICE_UUID_FULL):
                data = raw.service_data.get(k)
                if data is None:
                    continue
                try:
                    decoded = data.decode("utf-8", errors="strict")
                except UnicodeDecodeError:
                    continue
                low = decoded.lower()
                if low.startswith("dreame"):
                    miio_brand = "dreame"
                    miio_payload_str = decoded
                    break
                if low.startswith("mova"):
                    miio_brand = "mova"
                    miio_payload_str = decoded
                    break

        if not (legacy_uuid or name_match or miio_brand):
            return None

        metadata: dict = {"vendor": "Dreame"}

        if name_match:
            metadata["serial"] = name_match.group(1)
            metadata["device_name"] = local_name
            metadata["product_path"] = "legacy"
        elif legacy_uuid:
            metadata["product_path"] = "legacy"

        if miio_brand:
            metadata["product_path"] = "miio_provisioning"
            metadata["brand"] = miio_brand
            if miio_payload_str:
                metadata["miio_payload"] = miio_payload_str
            metadata["provisioning_mode"] = True
        elif miio_uuid and not (legacy_uuid or name_match):
            # MiIO UUID present but no Dreame brand prefix and no other
            # Dreame signal — NOT a Dreame device.
            return None

        device_class = "lawn_mower" if miio_brand == "mova" else "vacuum"

        id_basis = f"dreame:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="dreame",
            beacon_type="dreame",
            device_class=device_class,
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )
