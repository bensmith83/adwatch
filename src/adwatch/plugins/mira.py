"""Mira hormone monitor / fertility analyzer plugin.

Per apk-ble-hunting/reports/mira-fertilitytracker-android-us_passive.md.

Discovery is **device-name only**: the app installs two ``ScanFilter`` entries
matching the *exact* names ``Mira-Analyzer`` and ``EVA3000``. There is no
manufacturer-data or service-data parsing anywhere in the decompiled tree, and
no service-UUID scan filter — the primary service (``0000FFF0`` / Nordic UART
``6E400001``) is only discovered after connecting, and both are far too generic
to register as a Mira signal on their own.

The ``A5…D0E0…`` frame markers in the app are **post-connect** FFF1/NUS
characteristic framing, not advertisement content (the report corrects an
earlier analysis on this point) — nothing here decodes them.

Hormone results (LH / E3G / PdG) require a connection; nothing is broadcast.

Privacy: the static, product-identifying name lets any passive observer infer
the presence of a fertility/hormone monitor, and reconnect uses a fixed MAC,
so a specific analyzer is trackable. Flagged ``sensitive=True``.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


# Exact names, as the app matches them (ScanFilter.setDeviceName is exact).
MIRA_NAMES = {
    "Mira-Analyzer": "Mira-Analyzer",
    "EVA3000": "EVA3000",
}
MIRA_NAME_PATTERN = r"^(Mira-Analyzer|EVA3000)$"


@register_parser(
    name="mira",
    local_name_pattern=MIRA_NAME_PATTERN,
    description="Mira / EVA3000 hormone & fertility analyzer (presence-only)",
    version="1.0.0",
    core=False,
)
class MiraParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        local_name = raw.local_name or ""
        model = MIRA_NAMES.get(local_name)
        if model is None:
            return None

        metadata: dict = {
            "vendor": "Mira",
            "model": model,
            "device_name": local_name,
            "telemetry": "none (connect-only GATT)",
            "sensitive": True,
            "sensitive_category": "reproductive_health",
        }

        # Nothing per-unit is broadcast; the app reconnects by fixed MAC, so
        # the MAC is the only (and expected-stable) per-unit anchor.
        id_hash = hashlib.sha256(
            f"mira:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="mira",
            beacon_type="mira",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
