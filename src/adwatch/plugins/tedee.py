"""Tedee smart-lock plugin.

Per apk-ble-hunting/reports/tedee-mobile_passive.md:

  - Tedee uses a custom 128-bit service-UUID base
    `XXXXXXXX-4899-489F-A301-FBEE544B1DB0` where the first 8 hex chars
    vary by service (the specific 16-bit handles aren't recoverable from
    the obfuscated APK; the SDK on github.com/tedee-com publishes them).
  - DFU mode: Nordic Secure DFU `0000FE59-0000-1000-8000-00805F9B34FB`.
  - Lock state is NOT broadcast — connection required for any control
    or state read.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


# Tedee vendor service-UUID base — the lower 96 bits are constant.
TEDEE_UUID_TAIL = "-4899-489f-a301-fbee544b1db0"
NORDIC_SECURE_DFU_UUID = "0000fe59-0000-1000-8000-00805f9b34fb"

_TEDEE_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-4899-489f-a301-fbee544b1db0$", re.IGNORECASE
)


@register_parser(
    name="tedee",
    service_uuid=NORDIC_SECURE_DFU_UUID,
    local_name_pattern=r"^Tedee( |$)",
    description="Tedee smart locks and bridges",
    version="1.0.0",
    core=False,
)
class TedeeParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        dfu_hit = NORDIC_SECURE_DFU_UUID in normalized
        # Detect any UUID under the Tedee vendor base.
        tedee_uuids = [u for u in normalized if _TEDEE_UUID_RE.match(u)]
        name_hit = bool(raw.local_name and raw.local_name.startswith("Tedee"))

        # Nordic DFU is shared across many vendors — only treat as Tedee if we
        # also have a name signal or a Tedee-base UUID. Otherwise this match
        # is too loose.
        if dfu_hit and not (name_hit or tedee_uuids):
            return None

        if not (tedee_uuids or name_hit or dfu_hit):
            return None

        metadata: dict = {}

        if tedee_uuids:
            metadata["tedee_service_uuids"] = tedee_uuids
            # The first 8 hex chars are the per-service handle.
            metadata["tedee_service_handle_hex"] = tedee_uuids[0][:8]

        if dfu_hit:
            metadata["dfu_mode"] = True

        if name_hit:
            metadata["device_name"] = raw.local_name
            # Surface model hint (Tedee / Tedee PRO / Tedee GO / Tedee Bridge).
            metadata["model_hint"] = raw.local_name

        # Identity prefers the per-service handle when present.
        if tedee_uuids:
            id_basis = f"tedee:{tedee_uuids[0][:8]}"
        else:
            id_basis = f"tedee:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="tedee",
            beacon_type="tedee",
            device_class="lock",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
