"""Philips DreamStation 2 CPAP plugin.

Per apk-ble-hunting/reports/philips-sleepmapper-root_passive.md.
DreamStation 2 advertises a single 128-bit vendor service UUID:

    22A4E311-A097-4517-9B81-CF32AF60B982

That UUID is the discovery primitive — no manufacturer-data, no service-
data, no name-based filtering by the app. Presence implies the user has
a DreamStation 2 CPAP nearby (PHI-by-inference, equivalent to the
ResMed myAir `0xFD56` signal).

Therapy state, alarms, AHI, pressure are all post-connect (Respironics
Binary Protocol).
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


DREAMSTATION2_UUID = "22a4e311-a097-4517-9b81-cf32af60b982"


@register_parser(
    name="philips_dreamstation",
    service_uuid=DREAMSTATION2_UUID,
    description="Philips DreamStation 2 CPAP",
    version="1.0.0",
    core=False,
)
class PhilipsDreamstationParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        if DREAMSTATION2_UUID not in normalized:
            return None

        metadata: dict = {
            "vendor": "Philips Respironics",
            "product_family": "DreamStation 2",
            "safety_critical": True,
        }
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        id_basis = f"philips_dreamstation:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="philips_dreamstation",
            beacon_type="philips_dreamstation",
            device_class="cpap",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
