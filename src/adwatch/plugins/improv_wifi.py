"""Improv Wi-Fi provisioner plugin (ESPHome ecosystem).

Per apk-ble-hunting/reports/homeassistant-companion-android_passive.md:
the Improv-Wifi spec defines a service UUID emitted by ESP32 / ESPHome
devices in Wi-Fi-provisioning mode. Home Assistant Android filters scans
for this UUID when the user starts "Add ESPHome device". A passive
scanner sees an Improv beacon as a strong "device is currently in setup
mode and willing to take Wi-Fi credentials" signal.

Spec: https://www.improv-wifi.com/ble/
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


IMPROV_SERVICE_UUID = "00467768-6228-2272-4663-277478268000"


@register_parser(
    name="improv_wifi",
    service_uuid=IMPROV_SERVICE_UUID,
    description="Improv-Wifi provisioning beacon (ESPHome / ESP32)",
    version="1.0.0",
    core=False,
)
class ImprovWifiParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        if IMPROV_SERVICE_UUID not in normalized:
            return None

        metadata: dict = {
            "ecosystem": "improv-wifi",
            "provisioning_mode": True,
        }
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        id_basis = f"improv_wifi:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="improv_wifi",
            beacon_type="improv_wifi",
            device_class="provisioning",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
