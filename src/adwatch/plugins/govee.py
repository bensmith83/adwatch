"""Govee Sensors BLE advertisement parser.

Layouts cross-checked against Home Assistant's govee-ble
(https://github.com/Bluetooth-Devices/govee-ble ``parser.py``) and the
Theengs decoder (``src/devices/H5072_json.h``, ``H5074_json.h``,
``H5102_json.h``), and verified on NearSight corpus captures — see
``docs/protocols/govee-sensor.md`` and ``docs/protocols/govee-ec88-0001.md``.

v1.3 corrections:

* **H5074** (7-byte 0xEC88 payload): temperature int16 LE at offset **1**,
  humidity uint16 LE at 3, battery at 5 (was 2/4/6, which decoded corpus
  frame ``88ec00fc0dc5086402`` as -150.9 C / 256.1 % instead of 35.80 C /
  22.45 % / 100 %).
* **H5072/H5075** (6-byte 0xEC88 payload ``00 <enc24> <batt> 00``):
  encoded value at offset **1**, battery at 4 (was 3 and 6, so no real
  6-byte capture ever decoded).
* **enc24 temperature** is ``(enc & 0x7FFFFF) // 1000 / 10`` as in
  govee-ble ``decode_temp_humid``; ``enc / 10000`` leaked the humidity
  digits into the temperature (256470 -> 25.647 instead of 25.6).
* **CID 0x0001 frames** on service UUID 0xEC88 (``01 00 | 01 01 | enc24 |
  batt``) are now decoded — govee-ble's H5100/H5101/H5102/H5104/H5105/
  H5108/H5174/H5177 path.  Battery is the low 7 bits; bit 7 is an error flag.
"""

import hashlib
import re
import struct

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig
from adwatch.registry import register_parser, _normalize_uuid

GOVEE_COMPANY_ID = 0xEC88
# Govee's H5100-family frames start ``01 00``, which the stack reads as
# company ID 0x0001 (not a real SIG assignment for Govee).
GOVEE_CID_0001 = 0x0001
_EC88_SERVICE_UUID = _normalize_uuid("ec88")
_GOVEE_NAME_RE = re.compile(r"^(GVH5|GV5|Govee)")
_NAME_MODEL_RE = re.compile(r"H?(5\d{3})")

# Apple iBeacon glued after the Govee payload when a scanner concatenates
# manufacturer-data structures; its 16-byte UUID is ASCII "INTELLI_ROCKS_HW"
# and its 2-byte major carries two more ASCII model chars ("Pu", "Qw").
_IBEACON_PREFIX = bytes.fromhex("4c000215")
_INTELLI_ROCKS = b"INTELLI_ROCKS_HW"
# Corpus inference (NearSight telemetry): the HWQw device also advertises as
# GVH5177_B1E1; HWPu rides on 6-byte 0xEC88 H5072/H5075 frames.
_IBEACON_MODEL_HINTS = {"HWPu": "H5075", "HWQw": "H5177"}

# govee-ble MIN_TEMP / MAX_TEMP sanity window.
_MIN_TEMP_C = -40
_MAX_TEMP_C = 100
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

def _decode_enc24(enc_bytes: bytes) -> tuple[float, float]:
    """govee-ble decode_temp_humid: 24-bit BE, bit 23 = negative."""
    base = int.from_bytes(enc_bytes[:3], "big")
    value = base & 0x7FFFFF
    temperature = (value // 1000) / 10.0
    if base & 0x800000:
        temperature = -temperature
    humidity = (value % 1000) / 10.0
    return temperature, humidity


def _split_ibeacon(data: bytes) -> tuple[bytes, str | None]:
    """Strip a glued iBeacon (``4c 00 02 15 ...``) and return its marker."""
    idx = data.find(_IBEACON_PREFIX)
    if idx <= 0:
        return data, None
    beacon_uuid = data[idx + 4:idx + 20]
    major = data[idx + 20:idx + 22]
    marker = None
    if beacon_uuid == _INTELLI_ROCKS and len(major) == 2:
        marker = "HW" + major.decode("ascii", "replace")
    return data[:idx], marker


# Minimum payload lengths per format
_FORMAT_MIN_LEN = {
    "h5074": 6,
    "h5075": 5,
    "h5103": 8,
    "h5177": 11,
    "h5181": 4,  # 2 prefix + at least 2 bytes for one probe
}


@register_parser(
    name="govee",
    company_id=[GOVEE_COMPANY_ID, GOVEE_VIBRATION_COMPANY_ID],
    service_uuid="ec88",
    local_name_pattern=r"^(GVH5|GV5124|Govee)",
    description="Govee Sensors",
    version="1.3.0",
    core=False,
)
class GoveeParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 2:
            return None

        company_id = int.from_bytes(raw.manufacturer_data[:2], "little")
        if company_id == GOVEE_CID_0001:
            return self._parse_cid_0001(raw)
        if company_id not in (GOVEE_COMPANY_ID, GOVEE_VIBRATION_COMPANY_ID):
            return None

        try:
            return self._parse_inner(raw, company_id)
        except struct.error:
            return None

    def _parse_inner(self, raw: RawAdvertisement, company_id: int) -> ParseResult | None:
        payload = raw.manufacturer_data[2:]

        # H512x encrypted format: 24 bytes after company ID
        if company_id == GOVEE_VIBRATION_COMPANY_ID or (
            len(payload) == 24 and self._is_h512x_name(raw.local_name)
        ):
            return self._parse_h512x(raw, payload)

        payload, ibeacon_marker = _split_ibeacon(payload)
        model, fmt = self._detect_model(raw.local_name)
        if model == "unknown" and len(payload) == 6:
            # govee-ble: a 6-byte 0xEC88 payload is the H5072/H5075 frame.
            model, fmt = "H5072/H5075", "h5075"

        min_len = _FORMAT_MIN_LEN.get(fmt, MIN_PAYLOAD_LEN)
        if len(payload) < min_len:
            return None

        if fmt == "h5181":
            return self._parse_meat_thermometer(raw, payload, model)

        sensor_error = False
        if fmt == "h5075":
            # 00 | enc24 | batt | 00  (govee-ble data[1:5], Theengs H5072)
            temperature, humidity = _decode_enc24(payload[1:4])
            battery = payload[4] & 0x7F
            sensor_error = bool(payload[4] & 0x80)
        elif fmt == "h5103":
            temperature, humidity = _decode_enc24(payload[4:7])
            battery = payload[7]
        elif fmt == "h5177":
            temperature = struct.unpack_from("<h", payload, 6)[0] / 100
            humidity = struct.unpack_from("<H", payload, 8)[0] / 100
            battery = payload[10]
        else:
            # H5074: 00 | temp int16 LE | hum uint16 LE | batt | 02
            # (govee-ble "<hHB" at data[1:6], Theengs H5074_json.h)
            temperature = struct.unpack_from("<h", payload, 1)[0] / 100
            humidity = struct.unpack_from("<H", payload, 3)[0] / 100
            battery = payload[5]

        metadata = {"model": model, "battery_percent": battery}
        if not sensor_error:
            metadata["temperature_c"] = temperature
            metadata["humidity_percent"] = humidity
        if fmt == "h5075":
            metadata["sensor_error"] = sensor_error
        if ibeacon_marker:
            metadata["ibeacon_marker"] = ibeacon_marker

        id_hash = hashlib.sha256(raw.mac_address.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="govee",
            beacon_type="govee",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata=metadata,
        )

    def _parse_cid_0001(self, raw: RawAdvertisement) -> ParseResult | None:
        """``01 00 | 01 01 | enc24 BE | batt`` on service UUID 0xEC88.

        govee-ble H5100-family path: decode_temp_humid_battery_error(data[2:6]);
        an 8-byte payload is the temperature-only H5108.  CID 0x0001 is shared
        with TPMS / iBBQ, so an EC88 service UUID or a Govee name is required.
        """
        name = raw.local_name or ""
        has_ec88 = any(
            _normalize_uuid(u) == _EC88_SERVICE_UUID for u in (raw.service_uuids or [])
        )
        if not (has_ec88 or _GOVEE_NAME_RE.match(name)):
            return None

        payload, ibeacon_marker = _split_ibeacon(raw.manufacturer_data[2:])
        if len(payload) not in (6, 8):
            return None

        temperature, humidity = _decode_enc24(payload[2:5])
        battery = payload[5] & 0x7F
        sensor_error = bool(payload[5] & 0x80)

        name_model = _NAME_MODEL_RE.search(name) if _GOVEE_NAME_RE.match(name) else None
        if len(payload) == 8:
            model, model_source = "H5108", "payload_length"
        elif name_model:
            model, model_source = f"H{name_model.group(1)}", "local_name"
        elif ibeacon_marker in _IBEACON_MODEL_HINTS:
            model, model_source = _IBEACON_MODEL_HINTS[ibeacon_marker], "ibeacon_marker"
        else:
            model, model_source = "unknown", None

        metadata = {
            "model": model,
            "frame_format": "govee_cid_0001",
            "battery_percent": battery,
            "sensor_error": sensor_error,
        }
        if model_source:
            metadata["model_source"] = model_source
        if not sensor_error and _MIN_TEMP_C <= temperature <= _MAX_TEMP_C:
            metadata["temperature_c"] = temperature
            if model != "H5108":  # temperature-only probe (Theengs GV5108)
                metadata["humidity_percent"] = humidity
        if ibeacon_marker:
            metadata["ibeacon_marker"] = ibeacon_marker

        id_hash = hashlib.sha256(raw.mac_address.encode()).hexdigest()[:16]
        return ParseResult(
            parser_name="govee",
            beacon_type="govee",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata=metadata,
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
