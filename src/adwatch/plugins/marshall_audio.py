"""Marshall Bluetooth speaker BLE advertisement parser.

Zound Industries enrichment (apk-ble-hunting zoundindustries-marshallbt
report, baksmali of ``connectionservice/api/a``): manufacturer data under CID
0x065A or its byte-swap 0x5A06 (the app accepts both). Post-CID payload:
[0]=model type (BLEDevice.Type), [1]=color id, [8]==0x01 -> pairing mode.
Raw earbuds also advertise ``LE-MINOR III`` / ``LE-adidas Z.N.E. 01``.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig
from adwatch.registry import register_parser

MARSHALL_SERVICE_UUID = "fe8f"
QUALCOMM_COMPANY_ID = 0x0912

ZOUND_COMPANY_IDS = (0x065A, 0x5A06)
ZOUND_NAME_PATTERN = r"^(LE-|\[LE\])(MINOR III|adidas Z\.N\.E\. 01)"
_ZOUND_NAME_RE = re.compile(ZOUND_NAME_PATTERN)
_ZOUND_NAME_MODELS = {"MINOR III": "Minor III", "adidas Z.N.E. 01": "adidas Z.N.E. 01"}

# BLEDevice.Type value -> Zound internal codename
ZOUND_MODEL_TYPES = {
    0: "ARNOLD", 1: "FREEMAN", 3: "DESIR", 4: "SAXON", 5: "OWENS",
    6: "DUPLANTIS", 7: "SAMMY", 8: "TYLER_S", 9: "TYLER_M", 11: "LENNOX",
    12: "IGGY", 13: "INFINITE", 14: "EMBERTON_II", 15: "JETT", 16: "TYLER_L",
    17: "ASLLANI", 18: "FILIPPA", 19: "GAHAN", 20: "KALLA", 21: "MOON",
    23: "WATTS", 24: "PLANT", 25: "AMY_S", 26: "AMY_M", 27: "ROBYN",
    29: "TURNER", 30: "WEMBLEY", 34: "SMITH", 35: "WATERS", 36: "NINA",
    37: "NICKS_S", 38: "NICKS_M", 41: "LYKKE", 98: "ASLLANI_RAW", 99: "JETT_RAW",
}

KNOWN_MODELS = {
    "STANMORE", "STANMORE II", "STANMORE III",
    "ACTON", "ACTON II", "ACTON III",
    "WOBURN", "WOBURN II", "WOBURN III",
    "EMBERTON", "EMBERTON II",
    "KILBURN", "KILBURN II",
    "MIDDLETON",
    "WILLEN", "WILLEN II",
    "STOCKWELL", "STOCKWELL II",
    "MONITOR", "MONITOR II",
    "MAJOR", "MAJOR IV", "MAJOR V",
    "MINOR", "MINOR III", "MINOR IV",
    "MOTIF", "MOTIF II",
    "MODE", "MODE II",
}


@register_parser(
    name="marshall_audio",
    service_uuid=MARSHALL_SERVICE_UUID,
    company_id=ZOUND_COMPANY_IDS,
    local_name_pattern=ZOUND_NAME_PATTERN,
    description="Marshall / Zound Industries (Marshall, adidas, Urbanears) audio advertisements",
    version="1.1.0",
    core=False,
)
class MarshallAudioParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        zound = self._parse_zound(raw)
        if zound is not None:
            return zound

        has_uuid = (MARSHALL_SERVICE_UUID in (raw.service_uuids or [])) or \
                   (raw.service_data and MARSHALL_SERVICE_UUID in raw.service_data)

        if not has_uuid:
            return None

        # Verify it's likely a Marshall by checking local_name or company_id
        name = raw.local_name
        is_marshall = name and any(name.upper().startswith(m) for m in KNOWN_MODELS)
        has_qualcomm = (raw.manufacturer_data and len(raw.manufacturer_data) >= 2 and
                        int.from_bytes(raw.manufacturer_data[:2], "little") == QUALCOMM_COMPANY_ID)

        if not is_marshall and not has_qualcomm:
            return None

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:marshall_audio".encode()
        ).hexdigest()[:16]

        metadata: dict = {}
        if name:
            metadata["device_name"] = name
            metadata["model"] = name

        return ParseResult(
            parser_name="marshall_audio",
            beacon_type="marshall_audio",
            device_class="speaker",
            identifier_hash=id_hash,
            raw_payload_hex=raw.manufacturer_data[2:].hex() if raw.manufacturer_data and len(raw.manufacturer_data) > 2 else "",
            metadata=metadata,
        )

    def _parse_zound(self, raw: RawAdvertisement) -> ParseResult | None:
        metadata: dict = {}
        payload = raw.manufacturer_payload
        if raw.company_id in ZOUND_COMPANY_IDS and payload:
            model_type = payload[0]
            metadata["model_type"] = model_type
            metadata["model_codename"] = ZOUND_MODEL_TYPES.get(model_type, "Unknown")
            if len(payload) >= 2:
                metadata["color_id"] = payload[1]
            if len(payload) >= 9:
                metadata["pairing_mode"] = payload[8] == 0x01
        name = raw.local_name
        m = _ZOUND_NAME_RE.match(name) if name else None
        if m:
            metadata["model"] = _ZOUND_NAME_MODELS[m.group(2)]
        if not metadata:
            return None
        if name:
            metadata["device_name"] = name
            metadata.setdefault("model", name)

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:marshall_audio".encode()
        ).hexdigest()[:16]
        return ParseResult(
            parser_name="marshall_audio",
            beacon_type="marshall_audio",
            device_class="speaker",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex() if payload else "",
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
                ("marshall_audio", limit),
            )

        return router

    def ui_config(self):
        return PluginUIConfig(
            tab_name="Marshall",
            tab_icon="speaker",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Recent Marshall Sightings",
                    data_endpoint="/api/marshall_audio/recent",
                    render_hints={"columns": ["timestamp", "mac_address", "local_name", "model", "rssi_max", "sighting_count"]},
                ),
            ],
        )
