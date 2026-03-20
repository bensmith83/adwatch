"""ESP32 Wi-Fi Provisioning over BLE parser.

Detects devices running Espressif's unified provisioning manager (protocomm).
The service UUID 021a9004-0382-4aea-bff4-6b3f1c5adfb4 is advertised by
ESP-IDF firmware using BLE transport for Wi-Fi credential provisioning.

Characteristic UUIDs share the same base with varying bytes 2-3:
  021aff50-... proto-ver    Protocol version
  021aff51-... prov-session Security handshake (Sec0/Sec1/Sec2)
  021aff52-... prov-config  Wi-Fi SSID + passphrase
  021aff53-... prov-scan    Wi-Fi AP scan results

All payloads are Protobuf-encoded.  The advertisement itself carries no
structured data beyond the service UUID, so this parser extracts what we
can: the device name and any service data bytes present.
"""

import hashlib

from adwatch.models import ParseResult, PluginUIConfig, RawAdvertisement, WidgetConfig
from adwatch.registry import register_parser

ESP_PROV_SERVICE_UUID = "021a9004-0382-4aea-bff4-6b3f1c5adfb4"


@register_parser(
    name="esp_prov",
    service_uuid=ESP_PROV_SERVICE_UUID,
    description="ESP32 Wi-Fi Provisioning (protocomm) advertisements",
    version="1.0.0",
    core=False,
)
class EspProvParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        # Match on advertised service UUID list
        uuid_lower = ESP_PROV_SERVICE_UUID.lower()
        found_in_uuids = uuid_lower in [u.lower() for u in (raw.service_uuids or [])]
        found_in_data = raw.service_data and uuid_lower in raw.service_data

        if not found_in_uuids and not found_in_data:
            return None

        # Extract any service data bytes (often empty for this protocol)
        svc_bytes = b""
        if raw.service_data and uuid_lower in raw.service_data:
            svc_bytes = raw.service_data[uuid_lower]

        # Stable identity: MAC + device name (name is set by firmware)
        name = raw.local_name or ""
        id_hash = hashlib.sha256(
            f"{raw.mac_address}:{name}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="esp_prov",
            beacon_type="esp_wifi_prov",
            device_class="iot",
            identifier_hash=id_hash,
            raw_payload_hex=svc_bytes.hex(),
            metadata={
                "device_name": name,
                "service_data_len": len(svc_bytes),
            },
            event_type="esp_prov_sighting",
            storage_table="esp_prov_sightings",
            storage_row={
                "timestamp": raw.timestamp,
                "mac_address": raw.mac_address,
                "device_name": name,
                "identifier_hash": id_hash,
                "rssi": raw.rssi,
                "raw_payload_hex": svc_bytes.hex(),
            },
            stable_key=id_hash,
        )

    def storage_schema(self) -> str | None:
        return """CREATE TABLE IF NOT EXISTS esp_prov_sightings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    mac_address TEXT NOT NULL,
    device_name TEXT,
    identifier_hash TEXT NOT NULL,
    rssi INTEGER,
    raw_payload_hex TEXT
);"""

    def api_router(self, db=None):
        if db is None:
            return None

        from fastapi import APIRouter, Query

        router = APIRouter()

        @router.get("/recent")
        async def recent(limit: int = Query(50, ge=1, le=500)):
            return await db.fetchall(
                "SELECT * FROM esp_prov_sightings ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )

        return router

    def ui_config(self):
        return PluginUIConfig(
            tab_name="ESP Prov",
            tab_icon="wifi",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="ESP32 Wi-Fi Provisioning Devices",
                    data_endpoint="/api/esp_prov/recent",
                    render_hints={"columns": ["timestamp", "mac_address", "device_name", "rssi"]},
                ),
            ],
        )
