"""Arccos Golf grip sensor / Link hub / rangefinder advertisement parser.

Per apk-ble-hunting/reports/arccosgolf-androidflagship_passive.md.

Arccos grip Smart Sensors are unusual: **live shot telemetry is broadcast in
the advertisement**, no connection required. The app slices the raw scan
record at fixed absolute offsets in
`agshotdetection/util/BluetoothParser.parseScanRecord`, gated on the 16-bit
Service-UUID list reading `F0 FF` (= `0xFFF0`) at record bytes [20..21].

Offset mapping. The telemetry blob starts at record byte [5], immediately
after an AD header at [3..4]; the report's leading hypothesis (and the only
one consistent with the app reinterpreting [5..6] as ID bytes rather than a
company ID) is that the AD type at [4] is `0xFF`, Manufacturer-Specific. The
BLE stack therefore hands us the whole blob as `manufacturer_data`, with the
first two ID bytes parsed as a bogus per-sensor "company ID":

    manufacturer_data[i] == scan_record[5 + i]

so sensor ID = `manufacturer_data[0:6]`, battery/movement = `[6]`, and so on.
Because that pseudo-CID is per-sensor, this plugin cannot register on a
company ID — it registers on the `0xFFF0` service UUID (plus the Link /
rangefinder name regexes) and gates hard inside `parse()`, since `0xFFF0` is
a generic squatted UUID shared with several unrelated products.

The Link / Link Pro hub and the rangefinder broadcast **no** telemetry; they
carry a fixed hex unit ID in the local name only.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import _normalize_uuid, register_parser


ARCCOS_SERVICE_UUID = "fff0"
_ARCCOS_UUID_NORMALIZED = _normalize_uuid(ARCCOS_SERVICE_UUID)

SHOT_TYPES = {
    1: "WAKE",
    2: "HIT",
    3: "SLEEP",
    4: "BUTTON_PRESS",
}

# Un-provisioned TI CC254x keyfobs are explicitly rejected by the app
# (`BtLeService.firmwareVersionIsValid`).
REJECTED_NAME = "TI BLE Keyfob"

ARCCOS_NAME_PATTERN = r"(?i)^(arccos link|link[0-9a-f]{4}|lnk3[0-9a-f]{4}|rf[0-9a-f]{4})$"
_LINK_GENERIC_RE = re.compile(r"(?i)^arccos link$")
_LINK_ID_RE = re.compile(r"(?i)^(?:link|lnk3)([0-9a-f]{4})$")
_RANGEFINDER_RE = re.compile(r"(?i)^rf([0-9a-f]{4})$")

_MIN_SENSOR_FRAME = 13


def _signed(value: int) -> int:
    return value - 256 if value >= 128 else value


@register_parser(
    name="arccos_golf",
    service_uuid=ARCCOS_SERVICE_UUID,
    local_name_pattern=ARCCOS_NAME_PATTERN,
    description="Arccos Golf grip Smart Sensors (shot telemetry) + Link hub / rangefinder",
    version="1.0.0",
    core=False,
)
class ArccosGolfParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        name = raw.local_name or ""

        sensor = self._parse_grip_sensor(raw, name)
        if sensor is not None:
            return sensor
        return self._parse_named_unit(raw, name)

    # --- grip Smart Sensor -------------------------------------------------
    def _parse_grip_sensor(self, raw: RawAdvertisement, name: str) -> ParseResult | None:
        if name == REJECTED_NAME:
            return None

        has_uuid = any(
            _normalize_uuid(u) == _ARCCOS_UUID_NORMALIZED
            for u in (raw.service_uuids or [])
        )
        if not has_uuid:
            return None

        data = raw.manufacturer_data
        if not data or len(data) < _MIN_SENSOR_FRAME:
            return None

        shot_type_value = data[7]
        if shot_type_value not in SHOT_TYPES:
            return None

        battery = (data[6] >> 1) & 0x7F
        if battery > 100:
            return None

        sensor_id = data[0:6]
        sensor_hex = sensor_id.hex()
        flags = data[9]

        metadata: dict = {
            "vendor": "Arccos",
            "device_role": "grip_sensor",
            "sensor_id": sensor_hex,
            "sensor_mac_style": ":".join(f"{b:02x}" for b in sensor_id),
            "battery_level": battery,
            "movement": bool(data[6] & 0x01),
            "shot_type_value": shot_type_value,
            "shot_type": SHOT_TYPES[shot_type_value],
            "is_shot": shot_type_value == 2,
            "seconds_since_shot": data[8],
            "hitcount": (flags >> 4) & 0x0F,
            "xyz_valid": bool((flags >> 3) & 1),
            "reset_flag": bool((flags >> 2) & 1),
            "reset_reason": flags & 0x03,
            "accel_x": _signed(data[10]),
            "accel_y": _signed(data[11]),
            "accel_z": _signed(data[12]),
        }
        if name:
            metadata["device_name"] = name

        id_basis = f"arccos:{sensor_hex}"
        return ParseResult(
            parser_name="arccos_golf",
            beacon_type="arccos_golf",
            device_class="fitness_sensor",
            identifier_hash=hashlib.sha256(id_basis.encode()).hexdigest()[:16],
            raw_payload_hex=data.hex(),
            metadata=metadata,
            # Telemetry changes every advert; dedup on the sensor identity.
            stable_key=id_basis,
        )

    # --- Link hub / rangefinder (name-only) --------------------------------
    def _parse_named_unit(self, raw: RawAdvertisement, name: str) -> ParseResult | None:
        if not name:
            return None

        unit_id = None
        if _LINK_GENERIC_RE.match(name):
            role = "link_hub"
        elif (m := _LINK_ID_RE.match(name)):
            role = "link_hub"
            unit_id = m.group(1)
        elif (m := _RANGEFINDER_RE.match(name)):
            role = "rangefinder"
            unit_id = m.group(1)
        else:
            return None

        metadata: dict = {
            "vendor": "Arccos",
            "device_role": role,
            "device_name": name,
            "telemetry": "connect_required_nus",
        }
        if unit_id:
            metadata["unit_id"] = unit_id

        prefix = "link" if role == "link_hub" else "rangefinder"
        id_basis = f"arccos:{prefix}:{unit_id}" if unit_id else f"arccos:{prefix}:{raw.mac_address}"

        return ParseResult(
            parser_name="arccos_golf",
            beacon_type="arccos_golf",
            device_class="fitness_sensor",
            identifier_hash=hashlib.sha256(id_basis.encode()).hexdigest()[:16],
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
            stable_key=id_basis,
        )

    def storage_schema(self):
        return None
