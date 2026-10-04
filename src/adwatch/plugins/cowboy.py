"""Cowboy e-bike (Cowboy 4 / Cross) presence plugin.

Per apk-ble-hunting/reports/cowboy-app_passive.md.

The bike is connect-oriented: lock state, battery and motor data are Modbus
streams over bonded GATT. No manufacturer- or service-data telemetry is
broadcast. The only passive fingerprint is the vendor 128-bit service UUID
``C0B0A000-18EB-499D-B266-2F2910744274`` (low-medium confidence that it is
actually advertised rather than GATT-only — needs live capture). The local
name is a user-set nickname, so it is reported but never matched on.

Privacy: identifies ownership of a high-value e-bike (theft targeting).
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


COWBOY_SERVICE_UUID = "c0b0a000-18eb-499d-b266-2f2910744274"


@register_parser(
    name="cowboy",
    service_uuid=COWBOY_SERVICE_UUID,
    description="Cowboy e-bike (presence-only, vendor service UUID)",
    version="1.0.0",
    core=False,
)
class CowboyParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        uuids = [u.lower() for u in (raw.service_uuids or [])]
        if COWBOY_SERVICE_UUID not in uuids:
            return None

        metadata: dict = {
            "vendor": "Cowboy",
            "product": "Cowboy e-bike",
            "telemetry": "none (lock/battery/motor are bonded-GATT only)",
            "confidence": "medium",
        }
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        # No in-payload identifier; MAC is the only anchor (rotation unknown).
        id_hash = hashlib.sha256(f"cowboy:{raw.mac_address}".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="cowboy",
            beacon_type="cowboy",
            device_class="vehicle",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
