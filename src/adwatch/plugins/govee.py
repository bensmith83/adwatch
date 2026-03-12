"""Govee Sensors BLE advertisement parser."""

import hashlib
import struct

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig
from adwatch.registry import register_parser

GOVEE_COMPANY_ID = 0xEC88
GOVEE_VIBRATION_COMPANY_ID = 0xEF88
MIN_PAYLOAD_LEN = 7  # default minimum; some formats require more

# H512x encrypted sensor format (H5121-H5130 series)
_H512X_MODEL_IDS = {
    3: "H5121",   # motion
    8: "H5122",   # button
    2: "H5123",   # window
    9: "H5124",   # vibration
    10: "H5125",  # button
    11: "H5126",  # button
    13: "H5130",  # pressure
}


def _calculate_crc(data: bytes) -> int:
    crc = 0x1D0F
    for b in data:
        for s in range(7, -1, -1):
            mask = 0
            if (crc >> 15) ^ (b >> s) & 1:
                mask = 0x1021
            crc = ((crc << 1) ^ mask) & 0xFFFF
    return crc


def _decrypt_data(key: bytes, data: bytes) -> bytes:
    cipher = Cipher(algorithms.AES(key[::-1]), modes.ECB())
    decryptor = cipher.decryptor()
    return (decryptor.update(data[::-1]) + decryptor.finalize())[::-1]


def _encrypt_data(key: bytes, data: bytes) -> bytes:
    cipher = Cipher(algorithms.AES(key[::-1]), modes.ECB())
    encryptor = cipher.encryptor()
    return (encryptor.update(data[::-1]) + encryptor.finalize())[::-1]

# Minimum payload lengths per format
_FORMAT_MIN_LEN = {
    "h5074": 7,
    "h5075": 7,
    "h5103": 8,
    "h5177": 11,
    "h5181": 4,  # 2 prefix + at least 2 bytes for one probe
}


@register_parser(
    name="govee",
    company_id=[GOVEE_COMPANY_ID, GOVEE_VIBRATION_COMPANY_ID],
    local_name_pattern=r"^(GVH5|GV5124|Govee)",
    description="Govee Sensors",
    version="1.1.0",
    core=False,
)
class GoveeParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 2:
            return None

        company_id = int.from_bytes(raw.manufacturer_data[:2], "little")
        if company_id not in (GOVEE_COMPANY_ID, GOVEE_VIBRATION_COMPANY_ID):
            return None

        payload = raw.manufacturer_data[2:]

        # H512x encrypted format: 24 bytes after company ID
        if company_id == GOVEE_VIBRATION_COMPANY_ID or (
            len(payload) == 24 and self._is_h512x_name(raw.local_name)
        ):
            return self._parse_h512x(raw, payload)

        model, fmt = self._detect_model(raw.local_name)

        min_len = _FORMAT_MIN_LEN.get(fmt, MIN_PAYLOAD_LEN)
        if len(payload) < min_len:
            return None

        if fmt == "h5181":
            return self._parse_meat_thermometer(raw, payload, model)

        if fmt == "h5075":
            encoded = int.from_bytes(payload[3:6], "big")
            is_negative = bool(encoded & 0x800000)
            if is_negative:
                encoded &= ~0x800000
            temperature = encoded / 10000
            if is_negative:
                temperature = -temperature
            humidity = (encoded % 1000) / 10
            battery = payload[6]
        elif fmt == "h5103":
            encoded = int.from_bytes(payload[4:7], "big")
            is_negative = bool(encoded & 0x800000)
            if is_negative:
                encoded &= ~0x800000
            temperature = encoded / 10000
            if is_negative:
                temperature = -temperature
            humidity = (encoded % 1000) / 10
            battery = payload[7]
        elif fmt == "h5177":
            temperature = struct.unpack_from("<h", payload, 6)[0] / 100
            humidity = struct.unpack_from("<H", payload, 8)[0] / 100
            battery = payload[10]
        else:
            # H5074 format (default)
            temperature = struct.unpack_from("<h", payload, 2)[0] / 100
            humidity = struct.unpack_from("<H", payload, 4)[0] / 100
            battery = payload[6]

        id_hash = hashlib.sha256(raw.mac_address.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="govee",
            beacon_type="govee",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata={
                "model": model,
                "temperature_c": temperature,
                "humidity_percent": humidity,
                "battery_percent": battery,
            },
        )

    def _parse_meat_thermometer(
        self, raw: RawAdvertisement, payload: bytes, model: str
    ) -> ParseResult:
        num_probes = min((len(payload) - 2) // 2, 6)
        probes = []
        for i in range(num_probes):
            offset = 2 + i * 2
            temp = struct.unpack_from("<h", payload, offset)[0] / 100
            probes.append(temp)

        id_hash = hashlib.sha256(raw.mac_address.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="govee",
            beacon_type="govee",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata={
                "model": model,
                "probes": probes,
            },
        )

    def _detect_model(self, local_name: str | None) -> tuple[str, str]:
        if not local_name:
            return "unknown", "h5074"
        # Meat thermometers
        for suffix in ("5181", "5182", "5183"):
            if suffix in local_name:
                return f"H{suffix}", "h5181"
        # H5177/H5179
        for suffix in ("5177", "5179"):
            if suffix in local_name:
                return f"H{suffix}", "h5177"
        # H5103 series (offset 4)
        for suffix in ("5103", "5104", "5105"):
            if suffix in local_name:
                return f"H{suffix}", "h5103"
        # H5075 series (offset 3)
        for suffix in ("5075", "5072", "5100", "5101", "5102"):
            if suffix in local_name:
                return f"H{suffix}", "h5075"
        # H5074 series
        for suffix in ("5074", "5174"):
            if suffix in local_name:
                return f"H{suffix}", "h5074"
        return "unknown", "h5074"

    def _is_h512x_name(self, local_name: str | None) -> bool:
        if not local_name:
            return False
        return "GV5124" in local_name

    def _parse_h512x(self, raw: RawAdvertisement, payload: bytes) -> ParseResult | None:
        if len(payload) != 24:
            return None

        time_ms = payload[2:6]
        enc_data = payload[6:22]
        enc_crc = payload[22:24]

        computed_crc = _calculate_crc(enc_data)
        expected_crc = int.from_bytes(enc_crc, "big")
        if computed_crc != expected_crc:
            return None

        key = time_ms + bytes(12)
        try:
            decrypted = _decrypt_data(key, enc_data)
        except ValueError:
            return None

        model_id = decrypted[2]
        battery = decrypted[4]
        event = decrypted[5]

        model_name = _H512X_MODEL_IDS.get(model_id, f"H512x({model_id})")
        vibration = event == 1

        id_hash = hashlib.sha256(raw.mac_address.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="govee",
            beacon_type="govee",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata={
                "model": model_name,
                "battery_percent": battery,
                "vibration": vibration,
                "event_code": event,
            },
        )

    def api_router(self, db=None):
        if db is None:
            return None

        from fastapi import APIRouter, Query

        router = APIRouter()
        parser = self

        @router.get("/recent")
        async def recent(limit: int = Query(50, ge=1, le=500)):
            rows = await db.fetchall(
                "SELECT *, last_seen AS timestamp FROM raw_advertisements "
                "WHERE ad_type = ? ORDER BY last_seen DESC LIMIT ?",
                ("govee", limit),
            )
            enriched = []
            for row in rows:
                item = dict(row)
                mfr_hex = item.get("manufacturer_data_hex")
                if mfr_hex:
                    try:
                        mfr_data = bytes.fromhex(mfr_hex)
                        raw_ad = RawAdvertisement(
                            timestamp=item["timestamp"],
                            mac_address=item["mac_address"],
                            address_type=item.get("address_type", "random"),
                            manufacturer_data=mfr_data,
                            service_data=None,
                            local_name=item.get("local_name"),
                        )
                        result = parser.parse(raw_ad)
                        if result:
                            item.update(result.metadata)
                    except (ValueError, KeyError):
                        pass
                enriched.append(item)
            return enriched

        return router

    def ui_config(self) -> PluginUIConfig:
        return PluginUIConfig(
            tab_name="Govee",
            tab_icon="activity",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Govee Sensor Activity",
                    data_endpoint="/api/govee/recent",
                    render_hints={
                        "columns": [
                            "timestamp",
                            "mac_address",
                            "local_name",
                            "model",
                            "vibration",
                            "battery_percent",
                            "temperature_c",
                            "humidity_percent",
                            "rssi_max",
                            "sighting_count",
                        ],
                    },
                ),
            ],
            refresh_interval=10,
        )
