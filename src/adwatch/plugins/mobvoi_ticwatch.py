"""Mobvoi TicWatch (Wear OS smartwatch) BLE plugin.

Per apk-ble-hunting/reports/mobvoi-ticwatch_passive.md (app
``com.mobvoi.companion.aw``).

The companion app inverts the usual roles: the **phone** advertises and the
watch connects to it.  That phone-side advertisement is deliberately
uninformative — manufacturer data is company ID ``70`` followed by three
bytes freshly randomized per session (``Math.random()*254+1``), carrying no
serial, token, or account ID.  It is **not** matched here for two reasons:

  1. Company ID ``0x0046`` is MediaTek's SIG registration, not Mobvoi's (the
     report misattributes it; Mobvoi has no entry in the SIG list at all), so
     registering on it would claim unrelated MediaTek devices wholesale.
  2. Any three non-zero bytes satisfy the payload shape, so there is nothing
     left to gate on.

That leaves the watch itself, which advertises under its Wear OS firmware
name — ``TicWatch Pro``, ``TicWatch E``, ``TicWatch S``, sometimes with a
bracketed hardware suffix (``TicWatch Pro [A1B2C3]``).  Detection is
presence-only: no health telemetry, no vendor service UUID (the vendor
service ``735DC4FA-…`` is discoverable only after connecting), and no stable
in-advertisement identifier, so identity falls back to the MAC.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

# Documented only — see the module docstring for why this is not a matcher.
MOBVOI_COMPANION_COMPANY_ID = 0x0046

# \b keeps "TicWatchery" and other glued suffixes out.
TICWATCH_NAME_PATTERN = r"^TicWatch\b"

_TICWATCH_RE = re.compile(r"^TicWatch\b\s*(.*)$")
_SUFFIX_RE = re.compile(r"^(.*?)\s*\[([^\]]+)\]$")


@register_parser(
    name="mobvoi_ticwatch",
    local_name_pattern=TICWATCH_NAME_PATTERN,
    description="Mobvoi TicWatch Wear OS smartwatch advertisements",
    version="1.0.0",
    core=False,
)
class MobvoiTicwatchParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.local_name:
            return None
        match = _TICWATCH_RE.match(raw.local_name)
        if not match:
            return None

        metadata: dict = {
            "vendor": "Mobvoi",
            "platform": "Wear OS",
            "device_name": raw.local_name,
        }

        tail = match.group(1).strip()
        suffix_match = _SUFFIX_RE.match(tail)
        if suffix_match:
            tail = suffix_match.group(1).strip()
            metadata["name_suffix"] = suffix_match.group(2)
        if tail:
            metadata["model_hint"] = tail

        id_hash = hashlib.sha256(
            f"mobvoi_ticwatch:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="mobvoi_ticwatch",
            beacon_type="mobvoi_ticwatch",
            device_class="wearable",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
