"""Microsoft Connected Devices Platform (CDP) BLE advertisement parser."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig
from adwatch.registry import register_parser

MICROSOFT_COMPANY_ID = 0x0006

DEVICE_TYPE_NAMES = {
    1: "Xbox One",
    6: "Apple iPhone",
    7: "Apple iPad",
    8: "Android device",
    9: "Windows 10 Desktop",
    11: "Windows 10 Phone",
    12: "Linux",
    13: "Windows IoT",
    14: "Surface Hub",
    15: "Windows laptop",
    16: "Windows tablet",
}

DEVICE_CLASS_MAP = {
    1: "gaming_console",
    6: "phone",
    7: "tablet",
    8: "phone",
    9: "computer",
    11: "phone",
    12: "computer",
    13: "iot",
    14: "computer",
    15: "laptop",
    16: "tablet",
}

EXTENDED_STATUS_FLAGS = {
    0x01: "RemoteSessionsHosted",
    0x02: "RemoteSessionsNotHosted",
    0x04: "NearShareAuthPolicySameUser",
    0x08: "NearShareAuthPolicyPermissive",
}


@register_parser(
    name="microsoft_cdp",
    company_id=MICROSOFT_COMPANY_ID,
    description="Microsoft Connected Devices Platform advertisements",
    version="1.0.0",
    core=True,
)
class MicrosoftCDPParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 4:
            return None

        company_id = int.from_bytes(raw.manufacturer_data[:2], "little")
        if company_id != MICROSOFT_COMPANY_ID:
            return None

        payload = raw.manufacturer_data[2:]
        scenario_type = payload[0]
        version_and_device_type = payload[1]
        version = (version_and_device_type >> 5) & 0x07
        device_type = version_and_device_type & 0x1F

        payload_hex = payload.hex()
        id_hash = hashlib.sha256(
            f"{raw.mac_address}:{payload_hex}".encode()
        ).hexdigest()[:16]

        device_type_name = DEVICE_TYPE_NAMES.get(device_type, "Unknown")
        device_class = DEVICE_CLASS_MAP.get(device_type, "computer")

        metadata = {
            "scenario_type": scenario_type,
            "device_type": device_type,
            "device_type_name": device_type_name,
            "version": version,
        }

        if len(payload) >= 4:
            share_bits = payload[2] & 0x1F
            if share_bits == 0:
                metadata["nearby_share_mode"] = "My devices only"
            elif share_bits == 1:
                metadata["nearby_share_mode"] = "Everyone"
            else:
                metadata["nearby_share_mode"] = "Unknown"

            flags_byte = payload[3]
            metadata["bt_address_as_device_id"] = bool(flags_byte & 0x20)

            status_flags = []
            lower4 = flags_byte & 0x0F
            for bit_val, name in EXTENDED_STATUS_FLAGS.items():
                if lower4 & bit_val:
                    status_flags.append(name)
            metadata["extended_device_status"] = status_flags

        if len(payload) >= 8:
            metadata["salt_hex"] = payload[4:8].hex()

        if len(payload) >= 27:
            metadata["device_hash_hex"] = payload[8:27].hex()

        return ParseResult(
            parser_name="microsoft_cdp",
            beacon_type="microsoft_cdp",
            device_class=device_class,
            identifier_hash=id_hash,
            raw_payload_hex=raw.manufacturer_data.hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None

    def api_router(self, db=None):
        if db is None:
            return None

        from fastapi import APIRouter, Query

        router = APIRouter()
        parser = self

        @router.get("/recent")
        async def recent(limit: int = Query(50, ge=1, le=500)):
            rows = await db.fetchall(
                "SELECT *, last_seen AS timestamp FROM raw_advertisements WHERE ad_type = ? ORDER BY last_seen DESC LIMIT ?",
                ("microsoft_cdp", limit),
            )
            enriched = []
            for row in rows:
                item = dict(row)
                mfr_hex = item.get("manufacturer_data_hex")
                if mfr_hex:
                    try:
                        raw = RawAdvertisement(
                            timestamp=item["timestamp"],
                            mac_address=item["mac_address"],
                            address_type=item.get("address_type", "random"),
                            manufacturer_data=bytes.fromhex(mfr_hex),
                            service_data=None,
                        )
                        result = parser.parse(raw)
                        if result:
                            item.update(result.metadata)
                            item["device_class"] = result.device_class
                    except (ValueError, KeyError):
                        pass
                enriched.append(item)
            return enriched

        return router

    def ui_config(self):
        return PluginUIConfig(
            tab_name="Microsoft CDP",
            tab_icon="monitor",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Recent Microsoft CDP Devices",
                    data_endpoint="/api/microsoft_cdp/recent",
                    render_hints={
                        "columns": [
                            "timestamp",
                            "mac_address",
                            "device_type_name",
                            "device_class",
                            "nearby_share_mode",
                            "extended_device_status",
                            "rssi",
                        ],
                    },
                ),
            ],
        )
