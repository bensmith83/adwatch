"""Compex Mini EMS (muscle stimulator) plugin.

Per apk-ble-hunting/reports/yuyife-compex_passive.md.

The app's FastBle scan rule filters on **one** 128-bit service UUID and nothing
else — no name filter, no manufacturer-data or service-data parsing::

    BleScanRuleConfig.Builder()
        .setServiceUuids(new UUID[]{
            UUID.fromString("6E401570-B5A3-F393-E0A9-E50E24DCCA9E")})

The UUID is Nordic-UART-*derived*: it reuses the NUS 128-bit suffix
``B5A3-F393-E0A9-E50E24DCCA9E`` with a vendor-custom ``6E4015xx`` prefix, so it
must be matched in full — a stock Nordic UART peripheral (``6E400001-…``) is not
a Compex and is explicitly not claimed.

Battery, electrode contact, current intensity and mode all require a connected
GATT session speaking the 4-byte opcode protocol; nothing is broadcast. Every
Compex Mini advertises the same UUID, so only the MAC distinguishes units.

Privacy: presence discloses a muscle-stimulation therapy device.
Flagged ``sensitive=True``.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


COMPEX_SERVICE_UUID = "6e401570-b5a3-f393-e0a9-e50e24dcca9e"


@register_parser(
    name="compex",
    service_uuid=COMPEX_SERVICE_UUID,
    description="Compex Mini EMS muscle stimulator (presence-only)",
    version="1.0.0",
    core=False,
)
class CompexParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        uuid_hit = COMPEX_SERVICE_UUID in [
            u.lower() for u in (raw.service_uuids or [])
        ]
        if not uuid_hit and raw.service_data:
            uuid_hit = COMPEX_SERVICE_UUID in [
                k.lower() for k in raw.service_data
            ]
        if not uuid_hit:
            return None

        metadata: dict = {
            "vendor": "Compex",
            "product": "Compex Mini",
            "service_uuid": COMPEX_SERVICE_UUID,
            "telemetry": "none (connect-only GATT)",
            "sensitive": True,
            "sensitive_category": "muscle_stimulation",
        }
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        # The UUID is product-wide, so the MAC is the only per-unit anchor.
        id_hash = hashlib.sha256(
            f"compex:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="compex",
            beacon_type="compex",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
