"""Inkbird Sensors BLE advertisement parser (iBBQ / IBS-TH)."""

import hashlib
import re
import struct

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig
from adwatch.registry import register_parser

# iBBQ manufacturer_data layout (apk-ble-hunting easybbq/bbqgo passive
# reports; see plugins/ibbq.py for the full table): a 10-byte header --
# sub-opcode(1) + header(2) + flag(1) + device MAC(6) -- then 2 bytes per
# probe. The first 2 header bytes are what the BLE stack reports as the
# "company ID"; these devices carry no real SIG company ID.
IBBQ_HEADER_LEN = 10
# 0x8000 and the documented 0xFFF6 / 0xFFFF sentinels all mean "no probe".
DISCONNECTED_VALUE = -32768  # 0x8000 signed = probe not connected
IBBQ_ABSENT_VALUES = (DISCONNECTED_VALUE, -10, -1)
MIN_IBBQ_PAYLOAD = 2  # at least 1 probe (2 bytes)
MIN_IBS_TH_PAYLOAD = 4  # temp (2) + humidity (2)

# Encoding A (classic IBS-TH "sps"/"tps") -- apk-ble-hunting
# inkbird-inkbirdapp_passive.md, BluetoothDataParser.parseAdvData fed
# scanRecord hex .substring(28) (= byte 14) by IbsthPresenter.java:68. For the
# sps advert (flags | 0xFFF0 UUID | name "sps" | 0x0A 0xFF <9 bytes>) byte 14
# is manufacturer_data[0]: no SIG company ID, the "CID" bytes ARE temperature.
#   [0:2] temp int16 LE /100 C   [2:4] hum int16 LE /100 %RH
#   [4] sensor config            [7] battery %    [8] data flag (6 = must read)
IBS_TH_SENSOR_CONFIG = {
    0: "internal",
    1: "external_temp_internal_hum",
    2: "internal_temp_external_hum",
    3: "external_temp_external_hum",
}

# Exact-name whitelist / prefix rules from InkBluetoothScanManager.java:89-231.
# Only sps/tps have a pinned advert layout; the rest are identified by model
# name only (their byte-14 basis depends on a record layout we can't pin).
# iBBQ is also claimed by plugins/ibbq.py (pre-existing overlap).
INKBIRD_NAMED_MODEL_PATTERN = (
    r"ITH-|IBS-|IHT-|INT-|IDT-|INDT-|IBT-|ISC-|COBB-|ISVT-|BG-BT|ITC-312"
    r"|Ink@IAM-T|Inkbird@IBT-|INKBIRD@IBT-"
)
INKBIRD_NAME_PATTERN = rf"^(iBBQ|sps|tps$|{INKBIRD_NAMED_MODEL_PATTERN})"
_NAMED_RE = re.compile(rf"^({INKBIRD_NAMED_MODEL_PATTERN})")


@register_parser(
    name="inkbird",
    service_uuid="0000fff0-0000-1000-8000-00805f9b34fb",
    local_name_pattern=INKBIRD_NAME_PATTERN,
    description="Inkbird Sensors",
    version="1.1.0",
    core=False,
)
class InkbirdParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.local_name:
            return None

        try:
            if raw.local_name.startswith("iBBQ"):
                return self._parse_ibbq(raw)
            elif raw.local_name.startswith("sps") or raw.local_name == "tps":
                return self._parse_ibs_th(raw)
            elif _NAMED_RE.match(raw.local_name):
                return self._parse_named(raw)
        except struct.error:
            return None

        return None

    def _parse_named(self, raw: RawAdvertisement) -> ParseResult:
        id_hash = hashlib.sha256(raw.mac_address.encode()).hexdigest()[:16]
        mfr = raw.manufacturer_data or b""
        return ParseResult(
            parser_name="inkbird",
            beacon_type="inkbird",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=mfr.hex(),
            metadata={"device_type": "inkbird_named", "model": raw.local_name},
        )

    def _parse_ibbq(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < IBBQ_HEADER_LEN:
            return None

        payload = raw.manufacturer_data[IBBQ_HEADER_LEN:]
        if len(payload) < MIN_IBBQ_PAYLOAD:
            return None

        probe_count = len(payload) // 2
        metadata: dict[str, str | int | float | bool | None] = {
            "device_type": "ibbq",
            "probe_count": probe_count,
        }

        for i in range(probe_count):
            value = struct.unpack_from("<h", payload, i * 2)[0]
            if value in IBBQ_ABSENT_VALUES:
                metadata[f"probe_{i + 1}"] = None
            else:
                metadata[f"probe_{i + 1}"] = value / 10.0

        id_hash = hashlib.sha256(raw.mac_address.encode()).hexdigest()[:16]

        storage_row = {
            "timestamp": raw.timestamp,
            "mac_address": raw.mac_address,
            "device_type": "ibbq",
            "temperature": metadata.get("probe_1"),
            "humidity": None,
            "probe_count": probe_count,
            "probe_1": metadata.get("probe_1"),
            "probe_2": metadata.get("probe_2"),
            "probe_3": metadata.get("probe_3"),
            "probe_4": metadata.get("probe_4"),
            "identifier_hash": id_hash,
            "rssi": raw.rssi,
            "raw_payload_hex": payload.hex(),
        }

        return ParseResult(
            parser_name="inkbird",
            beacon_type="inkbird",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata=metadata,
            event_type="inkbird_reading",
            storage_table="inkbird_readings",
            storage_row=storage_row,
        )

    def _parse_ibs_th(self, raw: RawAdvertisement) -> ParseResult | None:
        mfr = raw.manufacturer_data
        if not mfr or len(mfr) < MIN_IBS_TH_PAYLOAD:
            return None

        temp_only = raw.local_name == "tps"
        temperature = struct.unpack_from("<h", mfr, 0)[0] / 100.0
        humidity = None if temp_only else struct.unpack_from("<h", mfr, 2)[0] / 100.0

        metadata: dict = {"device_type": "ibs_th", "temperature": temperature}
        if humidity is not None:
            metadata["humidity"] = humidity
        if len(mfr) >= 5 and not temp_only:
            metadata["sensor_config"] = IBS_TH_SENSOR_CONFIG.get(mfr[4], f"unknown_{mfr[4]}")
        if len(mfr) >= 8:
            metadata["battery"] = mfr[7]
        if len(mfr) >= 9:
            metadata["must_read"] = mfr[8] == 6

        id_hash = hashlib.sha256(raw.mac_address.encode()).hexdigest()[:16]

        storage_row = {
            "timestamp": raw.timestamp,
            "mac_address": raw.mac_address,
            "device_type": "ibs_th",
            "temperature": temperature,
            "humidity": humidity,
            "probe_count": 0,
            "probe_1": None,
            "probe_2": None,
            "probe_3": None,
            "probe_4": None,
            "identifier_hash": id_hash,
            "rssi": raw.rssi,
            "raw_payload_hex": mfr.hex(),
        }

        return ParseResult(
            parser_name="inkbird",
            beacon_type="inkbird",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=mfr.hex(),
            metadata=metadata,
            event_type="inkbird_reading",
            storage_table="inkbird_readings",
            storage_row=storage_row,
        )

    def storage_schema(self) -> str | None:
        return """CREATE TABLE IF NOT EXISTS inkbird_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    mac_address TEXT NOT NULL,
    device_type TEXT NOT NULL,
    temperature REAL,
    humidity REAL,
    probe_count INTEGER NOT NULL,
    probe_1 REAL,
    probe_2 REAL,
    probe_3 REAL,
    probe_4 REAL,
    identifier_hash TEXT NOT NULL,
    rssi INTEGER,
    raw_payload_hex TEXT
);"""

    def api_router(self, db=None):
        if db is None:
            return None

        from fastapi import APIRouter

        router = APIRouter()

        @router.get("/active")
        async def active_sensors():
            return await db.fetchall(
                """SELECT * FROM inkbird_readings
                   WHERE id IN (
                       SELECT MAX(id) FROM inkbird_readings GROUP BY mac_address
                   )
                   ORDER BY timestamp DESC"""
            )

        return router

    def ui_config(self) -> PluginUIConfig | None:
        return PluginUIConfig(
            tab_name="Inkbird",
            tab_icon="flame",
            widgets=[
                WidgetConfig(
                    widget_type="sensor_card",
                    title="Active Sensors",
                    data_endpoint="/api/inkbird/active",
                    render_hints={
                        "primary_field": "temperature",
                        "secondary_field": "humidity",
                        "badge_fields": ["device_type"],
                        "unit": "temperature",
                    },
                ),
            ],
            refresh_interval=30,
        )
