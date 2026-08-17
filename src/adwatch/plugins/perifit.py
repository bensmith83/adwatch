"""Perifit pelvic-floor biofeedback probe plugin.

Per apk-ble-hunting/reports/starshipproduct-perifitmainapp_passive.md.

The React-Native bundle scans **unfiltered** (`startDeviceScan(null, null, …)`)
and selects devices purely by a case-insensitive ``startsWith`` test on the
advertised Local Name. An exhaustive grep of the bundle for ``manufacturerData``
/ ``serviceData`` / ``serviceUUIDs`` returns zero hits — there is no advertised
payload to decode. Pressure telemetry arrives as GATT notifications on ``AA41``
after connecting.

App prefix list: ``Perifit``, ``Urgo``, ``Urg0``, ``Simple BLE``, ``SimpleBLE``.
Only the three brand prefixes are registered here. ``Simple BLE`` / ``SimpleBLE``
are TI/Nordic eval-kit default names; claiming them would label unrelated dev
boards as a pelvic-floor probe — an expensive false positive for a
sensitive-category device.

The app trims NUL bytes from name-like strings, hinting some firmware
NUL-pads the advertised name, so the name is stripped before use.

Privacy: the brand-revealing Local Name discloses that the wearer uses a
pelvic-floor biofeedback probe. Flagged ``sensitive=True``.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


# (prefix, label, must_not_be_followed_by_a_letter). `Perifit` is distinctive
# enough that any suffix is accepted; the 4-char `Urgo`/`Urg0` prefixes are
# only accepted as a whole word or with a non-alphabetic suffix so that
# unrelated names such as "Urgonomics" are not claimed.
_BRAND_PREFIXES = (
    ("perifit", "Perifit", False),
    ("urgo", "Urgo (OEM rebrand)", True),
    ("urg0", "Urgo (OEM rebrand)", True),
)
PERIFIT_NAME_PATTERN = r"(?i)^(Perifit|Urg[o0])"


@register_parser(
    name="perifit",
    local_name_pattern=PERIFIT_NAME_PATTERN,
    description="Perifit / Urgo pelvic-floor biofeedback probe (presence-only)",
    version="1.0.0",
    core=False,
)
class PerifitParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        # Firmware may NUL-pad the advertised name; the app strips it too.
        local_name = (raw.local_name or "").replace("\x00", "").strip()
        if not local_name:
            return None

        lowered = local_name.lower()
        brand_variant = None
        for prefix, label, no_letter_suffix in _BRAND_PREFIXES:
            if not lowered.startswith(prefix):
                continue
            rest = lowered[len(prefix):]
            if no_letter_suffix and rest and rest[0].isalpha():
                continue
            brand_variant = label
            break
        if brand_variant is None:
            return None

        metadata: dict = {
            "vendor": "Perifit",
            "brand_variant": brand_variant,
            "device_name": local_name,
            "telemetry": "none (connect-only GATT)",
            "sensitive": True,
            "sensitive_category": "reproductive_health",
        }

        # No advertised payload at all, so the MAC is the only per-unit anchor.
        id_hash = hashlib.sha256(
            f"perifit:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="perifit",
            beacon_type="perifit",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
