"""SharkNinja Wi-Fi robot vacuum provisioning plugin.

Per apk-ble-hunting/reports/sharkninja-shark_passive.md: Shark robot
vacuums in Wi-Fi-provisioning mode advertise the SIG-allocated SharkNinja
service UUID ``0xFCBB``. Once paired, BLE advertising stops, so a hit
strongly implies the device is in onboarding mode.

Per the report, byte-level decode of the advertisement payload is in
``libsharkclean_android.so`` (Stage 6 candidate) — surfaced here as
provisioning-mode-only presence detection.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


SHARKNINJA_SERVICE_UUID = "fcbb"
_SHARKNINJA_FULL = "0000fcbb-0000-1000-8000-00805f9b34fb"


@register_parser(
    name="sharkninja",
    service_uuid=SHARKNINJA_SERVICE_UUID,
    description="SharkNinja Wi-Fi robot vacuum (provisioning beacon)",
    version="1.0.0",
    core=False,
)
class SharkNinjaParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        if SHARKNINJA_SERVICE_UUID not in normalized and _SHARKNINJA_FULL not in normalized:
            return None

        metadata: dict = {
            "vendor": "SharkNinja",
            "provisioning_mode": True,
        }
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        id_basis = f"sharkninja:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="sharkninja",
            beacon_type="sharkninja",
            device_class="vacuum",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
