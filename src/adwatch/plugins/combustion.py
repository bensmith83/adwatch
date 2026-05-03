"""Combustion Inc predictive thermometer plugin.

Byte layouts and product enums per
apk-ble-hunting/reports/combustion-app_passive.md.

Combustion publishes their BLE protocol — temperatures broadcast in
plaintext. A passive scanner gets full per-sensor cook telemetry.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


COMBUSTION_COMPANY_ID = 0x09C7
COMBUSTION_SERVICE_UUID = "00000100-caab-3792-3d44-97ae51c1407a"

PRODUCT_TYPES = {
    0x00: "UNKNOWN",
    0x01: "PROBE",
    0x02: "NODE",
    0x03: "GAUGE",
}

# Mode/color/id byte bit-layout (offset 18 of probe). Exact masks verified by
# the Kotlin source; if Combustion ever rebalances the bitfields these will
# need re-checking.
PROBE_MODES = {0: "NORMAL", 1: "INSTANT", 2: "REFERENCE"}
PROBE_COLORS = {0: "YELLOW", 1: "GREY", 2: "RED", 3: "BLUE", 4: "GREEN", 5: "ORANGE", 6: "PURPLE", 7: "BLACK"}

DFU_NAME_PREFIXES = {
    "Thermom_DFU_": "Probe",
    "Display_DFU_": "Display",
    "Charger_DFU_": "Charger",
    "Gauge_DFU_": "Gauge",
}
DFU_LEGACY_NAMES = {
    "CI Probe BL": "Probe",
    "CI Timer BL": "Display",  # legacy display/charger
    "CI Gauge BL": "Gauge",
}

_DFU_PREFIX_RE = re.compile(
    r"^(Thermom|Display|Charger|Gauge)_DFU_(.+)$"
)


def decode_temperatures_13bit(packed: bytes) -> list[float]:
    """Decode 8x 13-bit temperature values from 13 bytes (little-endian bit-packed).

    Returns °C using Combustion's standard formula: T = raw * 0.05 - 20.
    """
    bits = int.from_bytes(packed, "little")
    out: list[float] = []
    mask = (1 << 13) - 1
    for i in range(8):
        raw = (bits >> (i * 13)) & mask
        out.append(raw * 0.05 - 20.0)
    return out


@register_parser(
    name="combustion",
    company_id=COMBUSTION_COMPANY_ID,
    service_uuid=COMBUSTION_SERVICE_UUID,
    local_name_pattern=r"^(Thermom_DFU_|Display_DFU_|Charger_DFU_|Gauge_DFU_|CI Probe BL|CI Timer BL|CI Gauge BL)",
    description="Combustion Inc predictive thermometer (Probe/Node/Gauge)",
    version="1.0.0",
    core=False,
)
class CombustionParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        metadata: dict = {}

        # DFU mode: name-prefix discovery, no mfr-data parsing.
        name = raw.local_name or ""
        if name in DFU_LEGACY_NAMES:
            metadata["dfu_mode"] = True
            metadata["dfu_class"] = DFU_LEGACY_NAMES[name]
            metadata["dfu_legacy"] = True
        else:
            m = _DFU_PREFIX_RE.match(name)
            if m:
                metadata["dfu_mode"] = True
                metadata["dfu_class"] = {"Thermom": "Probe", "Display": "Display",
                                         "Charger": "Charger", "Gauge": "Gauge"}[m.group(1)]
                metadata["dfu_suffix"] = m.group(2)

        payload = raw.manufacturer_payload
        identity_basis = None

        if payload and len(payload) >= 1:
            ptype = payload[0]
            metadata["product_type_code"] = ptype
            metadata["product_type"] = PRODUCT_TYPES.get(ptype, f"UNKNOWN_{ptype}")

            if ptype in (0x01, 0x02) and len(payload) >= 21:
                serial = int.from_bytes(payload[1:5], "little")
                temps = decode_temperatures_13bit(payload[5:18])
                mode_color_id = payload[18]
                status = payload[19]
                hop = payload[20]

                metadata["serial_number"] = serial
                metadata["serial_hex"] = f"{serial:08x}"
                metadata["temperatures_c"] = [round(t, 3) for t in temps]
                metadata["mode_code"] = mode_color_id & 0x03
                metadata["mode"] = PROBE_MODES.get(mode_color_id & 0x03, "UNKNOWN")
                metadata["color_code"] = (mode_color_id >> 2) & 0x07
                metadata["color"] = PROBE_COLORS.get((mode_color_id >> 2) & 0x07, "UNKNOWN")
                metadata["probe_id"] = ((mode_color_id >> 5) & 0x07) + 1
                metadata["status_byte"] = status
                metadata["battery_low"] = bool(status & 0x01)
                metadata["hop_count"] = hop

                identity_basis = f"combustion:probe:{serial}"

            elif ptype == 0x03 and len(payload) >= 19:
                serial_bytes = payload[1:11]
                # Serial is ASCII per report (10 bytes). Strip nulls/whitespace.
                try:
                    serial_ascii = serial_bytes.decode("ascii").rstrip("\x00 ")
                except UnicodeDecodeError:
                    serial_ascii = serial_bytes.hex()
                temp_raw = int.from_bytes(payload[11:13], "little", signed=False)
                status = payload[13]
                alarms = int.from_bytes(payload[15:19], "little")

                metadata["serial_ascii"] = serial_ascii
                metadata["temperature_c"] = round(temp_raw * 0.05 - 20.0, 3)
                metadata["status_byte"] = status
                metadata["alarms"] = alarms

                identity_basis = f"combustion:gauge:{serial_ascii}"

        if identity_basis is None:
            # DFU or unknown — fall back to MAC + class.
            cls = metadata.get("dfu_class") or metadata.get("product_type") or "unknown"
            identity_basis = f"{raw.mac_address}:combustion:{cls}"

        id_hash = hashlib.sha256(identity_basis.encode()).hexdigest()[:16]
        raw_hex = payload.hex() if payload else ""

        return ParseResult(
            parser_name="combustion",
            beacon_type="combustion",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )

    def storage_schema(self):
        return None
