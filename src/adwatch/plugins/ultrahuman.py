"""Ultrahuman Ring AIR / Ring Pro / ProCharger BLE plugin.

Per apk-ble-hunting/reports/ultrahuman-android_passive.md (app
``com.ultrahuman.android``).

The ring managers scan with an empty ``ScanFilter`` list and then match in
software on the GAP name prefix, case-insensitively — so the advertised local
name is the only field the app consumes, and the only one available passively:

    uh_<id>   Ring AIR
    up_<id>   Ring Pro
    uc_<id>   ProCharger

The ``<id>`` suffix is emitted by firmware rather than built app-side and is
presumed to be a stable per-unit short ID, which makes it the identity basis
here (lower-cased, so the same ring hashes identically whichever case the
firmware advertises).  If that assumption is ever disproved by a live capture,
this is the line to revisit — it would also mean the ring is *not* trackable
by name across MAC rotation.

Deliberately not matched:

  - ``HOME_`` (Ultrahuman Home air-quality device) — the prefix is a common
    English word and the report documents no suffix format to gate on, so
    claiming it would mislabel unrelated devices.
  - The Ultrahuman M1 CGM's service UUID ``0xFDE3`` — the M1 is a rebadged
    Abbott sensor and ``plugins/tandem_pump.py`` already registers that UUID.
  - The AiDEX CGM's ``0x181F`` — vendor-agnostic SIG CGM profile.
  - The ``86f6…`` vendor GATT services — used only post-connect and not
    confirmed present in the advertisement.

No passive telemetry: battery/health state is read over an authenticated,
bonded GATT connection.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

# A suffix is required — a bare "uh_" carries no device identity.
ULTRAHUMAN_NAME_PATTERN = r"(?i)^(uh|up|uc)_(.+)$"

_ULTRAHUMAN_RE = re.compile(ULTRAHUMAN_NAME_PATTERN)

_PRODUCTS = {
    "uh": ("Ring AIR", "wearable"),
    "up": ("Ring Pro", "wearable"),
    "uc": ("ProCharger", "accessory"),
}


@register_parser(
    name="ultrahuman",
    local_name_pattern=ULTRAHUMAN_NAME_PATTERN,
    description="Ultrahuman Ring AIR / Pro / ProCharger advertisements",
    version="1.0.0",
    core=False,
)
class UltrahumanParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.local_name:
            return None
        match = _ULTRAHUMAN_RE.match(raw.local_name)
        if not match:
            return None

        prefix = match.group(1).lower()
        device_id = match.group(2)
        product, device_class = _PRODUCTS[prefix]

        metadata: dict = {
            "vendor": "Ultrahuman",
            "product": product,
            "name_prefix": f"{prefix}_",
            "device_id": device_id,
            "device_name": raw.local_name,
        }

        # Firmware case is not guaranteed, so normalize before hashing.
        id_hash = hashlib.sha256(
            f"ultrahuman:{prefix}_{device_id.lower()}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="ultrahuman",
            beacon_type="ultrahuman",
            device_class=device_class,
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
