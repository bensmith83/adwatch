"""PetPace Smart Collar BLE advertisement plugin.

Per apk-ble-hunting/reports/petpace_passive.md. The React-Native app's only
discovery primitive is an exact Complete-Local-Name equality test:

    e.filter(function(e){ return 'Collar' === e.name })

so the collar advertises the six-byte name ``Collar`` and nothing else that
is app-consumed. Vital signs (temperature, pulse, respiration, activity,
posture, HRV) travel as JSON over a GATT connection to service ``0xFE50``
after an opcode write — none of it is broadcast.

``0xFE50`` is SIG-assigned to Google and is shared by unrelated products, so
it is used here only to *raise confidence* in a name hit, never as a match
criterion of its own. Because every collar advertises the same generic name,
the MAC is the sole passive discriminator and therefore the identity basis.
"""

import hashlib

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import _normalize_uuid, register_parser


PETPACE_NAME = "Collar"
PETPACE_NAME_PATTERN = r"^Collar$"

# Advertised optionally; SIG-assigned to Google, so never a match on its own.
PETPACE_SERVICE_UUID = "0000fe50-0000-1000-8000-00805f9b34fb"
_PETPACE_SERVICE_NORM = _normalize_uuid(PETPACE_SERVICE_UUID)


@register_parser(
    name="petpace",
    local_name_pattern=PETPACE_NAME_PATTERN,
    description="PetPace Smart Collar (pet vital-signs monitor)",
    version="1.0.0",
    core=False,
)
class PetPaceParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        # equality, not prefix -- and case-sensitive, per the JS filter.
        if raw.local_name != PETPACE_NAME:
            return None

        has_service = any(
            _normalize_uuid(u) == _PETPACE_SERVICE_NORM
            for u in (raw.service_uuids or [])
        )

        metadata: dict = {
            "vendor": "PetPace",
            "model": "PetPace Smart Collar",
            "device_name": raw.local_name,
            "has_petpace_service": has_service,
            # Vitals are GATT-only; the advert carries no PHI.
            "telemetry_in_advert": False,
            # The name alone is generic, so flag how sure we are.
            "confidence": "high" if has_service else "low",
        }

        id_hash = hashlib.sha256(
            f"petpace:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="petpace",
            beacon_type="petpace",
            device_class="pet_tracker",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
