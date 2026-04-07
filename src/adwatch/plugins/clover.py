"""Clover payment terminal BLE advertisement parser."""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig, deserialize_service_data
from adwatch.registry import register_parser

CLOVER_COMPANY_ID = 0x0371

# Known Clover terminal model codes
MODEL_CODES = {
    "JB": "Clover Flex",
    "GB": "Clover Go",
    "MB": "Clover Mini",
    "SB": "Clover Station",
}

# Local name: CC{model_code}{serial}
CLOVER_NAME_PATTERN = re.compile(r"^CC([A-Z]{2})(\d+)$")


@register_parser(
    name="clover",
    company_id=CLOVER_COMPANY_ID,
    local_name_pattern=r"^CC[A-Z]{2}\d+",
    description="Clover POS payment terminal advertisements",
    version="1.0.0",
    core=False,
)
class CloverParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 4:
            return None

        if raw.company_id != CLOVER_COMPANY_ID:
            return None

        payload = raw.manufacturer_payload
        if not payload:
            return None

        id_hash = hashlib.sha256(
            f"clover:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        metadata: dict = {
            "payload_hex": payload.hex(),
            "payload_length": len(payload),
        }

        # Parse protocol version from first payload byte
        if len(payload) >= 1:
            metadata["protocol_version"] = payload[0]

        # Try to extract ASCII serial from payload (offset 6+)
        if len(payload) >= 7:
            serial_bytes = payload[6:]
            try:
                hw_serial = serial_bytes.decode("ascii")
                if hw_serial.isprintable() and len(hw_serial) > 0:
                    metadata["hardware_serial"] = hw_serial
            except UnicodeDecodeError:
                pass

        # Parse local name for model code and serial
        if raw.local_name:
            match = CLOVER_NAME_PATTERN.match(raw.local_name)
            if match:
                model_code, local_serial = match.groups()
                metadata["model_code"] = model_code
                metadata["model"] = MODEL_CODES.get(model_code, "Unknown")
                metadata["local_serial"] = local_serial

        return ParseResult(
            parser_name="clover",
            beacon_type="clover",
            device_class="payment_terminal",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
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
                ("clover", limit),
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
                            local_name=item.get("local_name"),
                        )
                        result = parser.parse(raw)
                        if result:
                            item.update(result.metadata)
                    except (ValueError, KeyError):
                        pass
                enriched.append(item)
            return enriched

        return router

    def ui_config(self):
        return PluginUIConfig(
            tab_name="Clover",
            tab_icon="credit-card",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Recent Clover Sightings",
                    data_endpoint="/api/clover/recent",
                    render_hints={"columns": ["timestamp", "local_name", "model", "local_serial", "hardware_serial", "rssi_max", "sighting_count"]},
                ),
            ],
        )
