"""Huami Mi Band / Amazfit / Zepp wearable plugin.

Per apk-ble-hunting/reports/xiaomi-hm-health_passive.md. Two service UUID
generations distinguish product lines:

  - **Mi Band 1-3** (legacy) — service UUID ``0x0000FEE0``
  - **Mi Band 4+ / Amazfit (Bip / GTR / GTS / T-Rex / Stratos / Verge)** —
    service UUID ``0000FED0-0000-3512-2118-0009AF100700`` (Huami-proprietary
    base)

Plus name patterns covering ``MI Band``, ``Mi Smart Band``, ``Amazfit``,
``Zepp``. The Mi Scale path (service-data ``0x181B`` / ``0x181D``) is
already handled by ``plugins/mi_scale.py``.

Advertisements are presence-only; HR/steps/sleep telemetry require a
post-connect authenticated session (Huami AES-128 challenge-response).
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


MIBAND_LEGACY_UUID = "0000fee0-0000-1000-8000-00805f9b34fb"
HUAMI_NEW_UUID = "0000fed0-0000-3512-2118-0009af100700"

_SHORT_LEGACY = "fee0"

_NAME_RE = re.compile(r"^(MI Band|Mi Smart Band|Amazfit|Zepp)\s*(.+)?$")


@register_parser(
    name="huami_amazfit",
    service_uuid=[MIBAND_LEGACY_UUID, HUAMI_NEW_UUID],
    local_name_pattern=r"^(MI Band|Mi Smart Band|Amazfit|Zepp)",
    description="Huami / Amazfit / Mi Band wearables",
    version="1.0.0",
    core=False,
)
class HuamiAmazfitParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        legacy_hit = MIBAND_LEGACY_UUID in normalized or _SHORT_LEGACY in normalized
        new_hit = HUAMI_NEW_UUID in normalized

        local_name = raw.local_name or ""
        name_match = _NAME_RE.match(local_name)

        if not (legacy_hit or new_hit or name_match):
            return None

        metadata: dict = {"vendor": "Huami"}

        if legacy_hit:
            metadata["product_family"] = "mi_band_legacy"
        elif new_hit:
            metadata["product_family"] = "huami_new"
        else:
            # Name-only fallback — be conservative.
            tag = name_match.group(1)
            metadata["product_family"] = (
                "mi_band_legacy" if tag.startswith("MI Band") else "huami_new"
            )

        if name_match:
            metadata["device_name"] = local_name
            tag = name_match.group(1)
            tail = (name_match.group(2) or "").strip()
            if tag == "Mi Smart Band":
                metadata["model_hint"] = f"Smart Band {tail}".strip()
            elif tag == "MI Band":
                metadata["model_hint"] = f"Band {tail}".strip()
            elif tail:
                metadata["model_hint"] = tail

        id_basis = f"huami_amazfit:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="huami_amazfit",
            beacon_type="huami_amazfit",
            device_class="wearable",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
