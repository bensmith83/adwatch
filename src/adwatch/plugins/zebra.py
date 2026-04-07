"""Zebra Technologies barcode scanner BLE advertisement parser."""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig, deserialize_service_data
from adwatch.registry import register_parser

ZEBRA_SERVICE_UUID = "fe79"

# Retailer-configured department codes observed in grocery stores
DEPARTMENT_CODES = {
    "PD": "Produce",
    "Pharm": "Pharmacy",
    "CA": "Checkout Area",
    "GM": "General Merchandise",
    "DL": "Deli",
    "BK": "Bakery",
    "MT": "Meat",
    "SF": "Seafood",
    "FL": "Floral",
    "DR": "Dairy",
    "FZ": "Frozen",
    "HB": "Health & Beauty",
    "WH": "Warehouse",
    "RX": "Pharmacy (RX)",
}

# Pattern: {store_number}_{department}{device_name}
# e.g., 096_PDZebra1, 096_CA_Floral, 096_PharmZebra
STORE_NAME_PATTERN = re.compile(r"^(\d{2,4})_([A-Za-z]+)_?(.*)$")


@register_parser(
    name="zebra",
    service_uuid=ZEBRA_SERVICE_UUID,
    description="Zebra Technologies enterprise barcode scanner advertisements",
    version="1.0.0",
    core=False,
)
class ZebraParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.service_uuids or ZEBRA_SERVICE_UUID not in [
            u.lower() for u in raw.service_uuids
        ]:
            return None

        id_hash = hashlib.sha256(
            f"zebra:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        metadata: dict = {}

        if raw.local_name:
            metadata["local_name"] = raw.local_name
            match = STORE_NAME_PATTERN.match(raw.local_name)
            if match:
                store_num, dept_code, device_suffix = match.groups()
                metadata["store_number"] = store_num

                # Try to split dept_code if it contains an embedded device name
                # e.g., "PDZebra" -> dept=PD, device=Zebra
                # e.g., "PharmZebra" -> dept=Pharm, device=Zebra
                split_done = False
                if dept_code not in DEPARTMENT_CODES:
                    for code in sorted(DEPARTMENT_CODES.keys(), key=len, reverse=True):
                        if dept_code.startswith(code) and len(dept_code) > len(code):
                            metadata["department_code"] = code
                            metadata["department"] = DEPARTMENT_CODES[code]
                            embedded_name = dept_code[len(code):]
                            # Combine embedded name with any suffix after underscore
                            metadata["device_name"] = embedded_name + device_suffix
                            split_done = True
                            break

                if not split_done:
                    metadata["department_code"] = dept_code
                    metadata["department"] = DEPARTMENT_CODES.get(dept_code, "Unknown")
                    if device_suffix:
                        metadata["device_name"] = device_suffix

        return ParseResult(
            parser_name="zebra",
            beacon_type="zebra",
            device_class="barcode_scanner",
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
        parser = self

        @router.get("/recent")
        async def recent(limit: int = Query(50, ge=1, le=500)):
            rows = await db.fetchall(
                "SELECT *, last_seen AS timestamp FROM raw_advertisements WHERE ad_type = ? ORDER BY last_seen DESC LIMIT ?",
                ("zebra", limit),
            )
            enriched = []
            for row in rows:
                item = dict(row)
                raw = RawAdvertisement(
                    timestamp=item["timestamp"],
                    mac_address=item["mac_address"],
                    address_type=item.get("address_type", "random"),
                    service_uuids=["fe79"],
                    local_name=item.get("local_name"),
                )
                result = parser.parse(raw)
                if result:
                    item.update(result.metadata)
                enriched.append(item)
            return enriched

        return router

    def ui_config(self):
        return PluginUIConfig(
            tab_name="Zebra",
            tab_icon="barcode",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Recent Zebra Sightings",
                    data_endpoint="/api/zebra/recent",
                    render_hints={"columns": ["timestamp", "local_name", "store_number", "department", "device_name", "rssi_max", "sighting_count"]},
                ),
            ],
        )
