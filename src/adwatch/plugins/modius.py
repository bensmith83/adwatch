"""Neurovalens Modius neurostimulation headset plugin.

Per apk-ble-hunting/reports/neurovalens-modius_passive.md.

The app's OS-level scan is unfiltered; every advertisement is delivered to Java
and accepted iff its **GAP device name** exactly equals one of the valid
identifiers (case-insensitive), or starts with one and ends in ``B``/``BL``
(bootloader / OTA mode). There is no manufacturer-data or service-data parsing
anywhere in ``com/neurovalens/nibs/``, and the 128-bit control service is not
used as a scan filter.

Variant map (``NIBSDeviceType.typeFromName``): names starting ``SLEEP`` →
Sleep, ``STRESS`` → Stress, everything else (``Slim``, legacy ``Modius``,
dev/legacy ``VESTAL``) → Slim.

The bootloader form is required here to be exactly ``<id>B`` or ``<id>BL``
rather than the app's looser "starts with id AND ends with B/BL", which would
also accept e.g. ``Slim B``. Real firmware uses the tight form, and the tight
form avoids claiming unrelated devices.

``Sleep`` / ``Stress`` / ``Slim`` are ordinary English words, so those carry
``confidence: medium``; the brand-specific ``Modius`` / ``VESTAL`` carry
``high``.

No telemetry is broadcast — battery, stimulation level, electrode resistance
and usage all require a bonded GATT connection. Two units of the same product
advertise the *same* name, so the MAC is the only per-unit identifier.

Privacy: presence discloses ownership of a sleep / anxiety / weight nerve-
stimulation medical device. Flagged ``sensitive=True``.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


# advertised id (lowercase) -> (product variant, firmware generation, confidence)
_MODIUS_IDS = {
    "sleep": ("Modius Sleep", "V2", "medium"),
    "stress": ("Modius Stress", "V2", "medium"),
    "slim": ("Modius Slim", "V2", "medium"),
    "modius": ("Modius Slim", "V1", "high"),
    "vestal": ("Modius Slim", "V1", "high"),
}
MODIUS_NAME_PATTERN = r"(?i)^(Sleep|Stress|Slim|Modius|VESTAL)(BL|B)?$"


@register_parser(
    name="modius",
    local_name_pattern=MODIUS_NAME_PATTERN,
    description="Neurovalens Modius Sleep/Stress/Slim neurostimulator",
    version="1.0.0",
    core=False,
)
class ModiusParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        local_name = (raw.local_name or "").strip()
        if not local_name:
            return None
        lowered = local_name.lower()

        entry = _MODIUS_IDS.get(lowered)
        bootloader = False
        if entry is None:
            for suffix in ("bl", "b"):
                if lowered.endswith(suffix):
                    entry = _MODIUS_IDS.get(lowered[: -len(suffix)])
                    if entry is not None:
                        bootloader = True
                        break
        if entry is None:
            return None

        variant, firmware, confidence = entry
        metadata: dict = {
            "vendor": "Neurovalens",
            "product_variant": variant,
            "firmware_generation": firmware,
            "bootloader_mode": bootloader,
            "device_name": local_name,
            "confidence": confidence,
            "telemetry": "none (connect-only GATT)",
            "sensitive": True,
            "sensitive_category": "neurostimulation",
        }

        # Units of the same product share a name, so the MAC is the only
        # per-unit anchor available passively.
        id_hash = hashlib.sha256(
            f"modius:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="modius",
            beacon_type="modius",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
