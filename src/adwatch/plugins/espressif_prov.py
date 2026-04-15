"""Espressif (ESP-IDF) BLE Wi-Fi provisioning service parser.

ESP-IDF's `wifi_prov_mgr` / `protocomm_ble` transport advertises a fixed
128-bit service UUID while the device is in unprovisioned mode. Used by
millions of ESP32-class smart plugs, bulbs, sensors, ESPHome devices and
hobby boards.
"""

import hashlib

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import register_parser

PROV_SERVICE_UUID = "021a9004-0382-4aea-bff4-6b3f1c5adfb4"
ESPRESSIF_COMPANY_ID = 0x02E5


@register_parser(
    name="espressif_prov",
    service_uuid=PROV_SERVICE_UUID,
    description="Espressif ESP-IDF BLE provisioning service",
    version="1.0.0",
    core=False,
)
class EspressifProvParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if PROV_SERVICE_UUID not in raw.service_uuids:
            return None

        metadata: dict = {}
        if raw.local_name:
            metadata["device_hint"] = raw.local_name
        if raw.company_id == ESPRESSIF_COMPANY_ID:
            metadata["vendor_confirmed"] = True

        id_hash = hashlib.sha256(
            f"espressif_prov:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="espressif_prov",
            beacon_type="espressif_prov",
            device_class="provisioning",
            identifier_hash=id_hash,
            raw_payload_hex=raw.manufacturer_data.hex() if raw.manufacturer_data else "",
            metadata=metadata,
        )
