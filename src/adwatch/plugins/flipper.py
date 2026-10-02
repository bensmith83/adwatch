"""Flipper Zero multi-tool BLE advertisement parser.

Per apk-ble-hunting flipperdevices-app report: the companion app identifies a
Flipper by local name prefix ``Flipper`` (full name ``Flipper <name>``) or the
Flipper Devices OUI ``80:E1:26``. The vendor Serial (protobuf RPC) service
``8fe5b3d5-2e7f-4a98-2a48-7acc60fe0000`` may also appear in the UUID list.
No manufacturer/service-data telemetry exists — presence/identity only.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig
from adwatch.registry import register_parser

FLIPPER_UUID = "3081"
FLIPPER_UUID_FULL = "00003081-0000-1000-8000-00805f9b34fb"
FLIPPER_SERIAL_UUID = "8fe5b3d5-2e7f-4a98-2a48-7acc60fe0000"
FLIPPER_SERVICE_UUIDS = [FLIPPER_UUID, FLIPPER_SERIAL_UUID]
FLIPPER_OUI = "80:E1:26"
FLIPPER_NAME_RE = re.compile(r"^Flipper")


@register_parser(
    name="flipper",
    service_uuid=FLIPPER_SERVICE_UUIDS,
    local_name_pattern=r"^Flipper",
    mac_prefix=FLIPPER_OUI,
    description="Flipper Zero multi-tool advertisements",
    version="1.1.0",
    core=False,
)
class FlipperParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        # Match on service UUID or local name
        uuids = {u.lower() for u in (raw.service_uuids or [])}
        uuid_match = FLIPPER_UUID_FULL in uuids or FLIPPER_UUID in uuids
        serial_match = FLIPPER_SERIAL_UUID in uuids
        name_match = raw.local_name is not None and FLIPPER_NAME_RE.search(raw.local_name)
        oui_match = raw.mac_address.upper().startswith(FLIPPER_OUI)

        if not (uuid_match or serial_match or name_match or oui_match):
            return None

        id_hash = hashlib.sha256(raw.mac_address.encode()).hexdigest()[:16]

        metadata: dict = {}
        if raw.local_name:
            metadata["device_name"] = raw.local_name
            if name_match:
                suffix = raw.local_name[len("Flipper"):].strip()
                if suffix:
                    metadata["flipper_name"] = suffix
        metadata["flipper_oui"] = oui_match
        if serial_match:
            metadata["serial_service"] = True

        return ParseResult(
            parser_name="flipper",
            beacon_type="flipper",
            device_class="tool",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )

    def storage_schema(self):
        return None

    def api_router(self, db=None):
        if db is None:
            return None

        from fastapi import APIRouter, Query

        router = APIRouter()

        @router.get("/recent")
        async def recent(limit: int = Query(50, ge=1, le=500)):
            return await db.fetchall(
                "SELECT *, last_seen AS timestamp FROM raw_advertisements WHERE ad_type = ? ORDER BY last_seen DESC LIMIT ?",
                ("flipper", limit),
            )

        return router

    def ui_config(self):
        return PluginUIConfig(
            tab_name="Flipper",
            tab_icon="cpu",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Recent Flipper Sightings",
                    data_endpoint="/api/flipper/recent",
                    render_hints={"columns": ["timestamp", "mac_address", "local_name", "rssi_max", "sighting_count"]},
                ),
            ],
        )
