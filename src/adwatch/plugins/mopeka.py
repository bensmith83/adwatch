"""Mopeka tank-level sensor plugin.

Per apk-ble-hunting/reports/mopeka-tankcheck_passive.md:

  Two co-existing wire formats keyed by 16-bit service UUID:

  - 0xFEE5 (nRF52 family: Pro / Pro+ / TopDown / H2O / Universal) — 12-byte
    manufacturer-data, full sensor telemetry.
  - 0xADA0 (CC2540 family: legacy STD / XL / BMPro) — 22 or 25-byte
    manufacturer-data with raw ultrasonic echo list.
  - 7F330000-5C9A-4440-9254-52FC43A694F1 (Mopeka Gateway) — 6-byte mfr-data
    with 0x44 0x2F magic.

  Mopeka does not have a SIG-registered company ID. The framework still
  treats bytes 0-1 of the manufacturer-data record as a CID, so this parser
  reads from `manufacturer_payload` (i.e. starting at the report's byte[2]).

  All sensor state — tank level, battery, temperature, sync-button — is
  broadcast in the unsolicited advertisement. Connection is only required
  for configuration writes.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


MOPEKA_NRF52_UUID = "fee5"
MOPEKA_CC2540_UUID = "ada0"
MOPEKA_GATEWAY_UUID = "7f330000-5c9a-4440-9254-52fc43a694f1"

# Hardware-version enum (nRF52). Bit 7 of byte[2] is the level extended-range
# flag; bits 0-6 are the variant id. The full hwVersionNumber is 0x100 | (b & 0x7F).
NRF52_HW_VARIANTS = {
    259: "PRO_MOPEKA",
    260: "TOPDOWN",
    261: "PRO_H2O",
    264: "PRO_PLUS_BLE_LPG",
    265: "PRO_PLUS_CELL_LPG",
    266: "PRO_PLUS_BLE_TD40",
    267: "PRO_PLUS_CELL_TD40",
    268: "PRO_UNIVERSAL",
}

# Quality stars (top 2 bits of the level word) → confidence label.
QUALITY_LABELS = {0: "no_reading", 1: "low", 2: "medium", 3: "high"}

# CC2540 accelerometer 4-bit signed lookup table (bundle constant).
_CC2540_ACCEL_LUT = [-7, 1, 2, 3, 4, 5, 6, 0, -6, -5, -8, 7, -4, -3, -2, -1]


def _parse_nrf52(payload: bytes) -> dict:
    """Decode the 10-byte nRF52 payload (post-CID strip)."""
    md: dict = {}
    if len(payload) < 10:
        return md

    hw_byte = payload[0]
    extended_range = bool(hw_byte & 0x80)
    hw_id = 0x100 | (hw_byte & 0x7F)
    md["hardware_id"] = hw_id
    md["hardware_variant"] = NRF52_HW_VARIANTS.get(hw_id, f"UNKNOWN_{hw_id}")
    md["extended_range"] = extended_range

    md["battery_voltage"] = round((payload[1] & 0x7F) / 32.0, 3)

    md["temperature_c"] = (payload[2] & 0x7F) - 40
    md["sync_pressed"] = bool(payload[2] & 0x80)

    level_word = payload[3] | (payload[4] << 8)
    raw_level = level_word & 0x3FFF
    if extended_range:
        md["level_meters"] = round((16384 + raw_level * 4) * 1e-6, 6)
    else:
        md["level_meters"] = round(raw_level * 1e-6, 6)
    quality = level_word >> 14
    md["quality_stars"] = quality
    md["reading_quality"] = QUALITY_LABELS.get(quality, "unknown")

    md["mac_tail_hex"] = payload[5:8].hex()

    md["accel_x"] = _signed_byte(payload[8]) / 16.0
    md["accel_y"] = _signed_byte(payload[9]) / 16.0
    return md


def _parse_cc2540(payload: bytes) -> dict:
    """Decode the 20- or 23-byte CC2540 payload (post-CID strip).

    Only the high-level fields (variant, battery, temp, sync, quality, MAC tail)
    are decoded — the 16-byte echo-list (offsets 4-19 here) is exposed as a hex
    blob since its 10-bit-packed form for hwVersion≥2 is rarely useful for
    passive observation outside the Mopeka app's UI.
    """
    md: dict = {}
    if len(payload) < 4:
        return md

    # Sentinel: byte[2] (in original numbering) == 0xAA → no-data filter
    # In our payload (post-CID) that's payload[0].
    if payload[0] == 0xAA:
        md["no_data_sentinel"] = True
        return md

    accel_byte = payload[0]
    md["accel_x"] = _CC2540_ACCEL_LUT[accel_byte & 0x0F]
    md["accel_y"] = _CC2540_ACCEL_LUT[(accel_byte >> 4) & 0x0F]

    hw_byte = payload[1]
    hw_id = hw_byte & 0xCF
    md["hardware_id"] = hw_id
    md["hardware_family"] = "xl" if (hw_byte & 0x01) else "gen2"
    if hw_id in (70, 72):
        # BMPro family encodes quality in bits 4-5 of byte[1].
        quality = (hw_byte >> 4) & 0x03
        md["quality_stars"] = quality
        md["reading_quality"] = QUALITY_LABELS.get(quality, "unknown")

    battery_raw = payload[2]
    md["battery_voltage"] = round(battery_raw / 256.0 * 2.0 + 1.5, 3)

    temp_raw = payload[3] & 0x3F
    if temp_raw == 0:
        md["temperature_c"] = -40
    else:
        md["temperature_c"] = round(1.776964 * (temp_raw - 25), 3)
    md["slow_update_rate"] = bool(payload[3] & 0x40)
    md["sync_pressed"] = bool(payload[3] & 0x80)

    # Corrupt-sample sentinel.
    if payload[3] == 0x3F and payload[2] == 0xFF:
        md["corrupted"] = True

    # Echo list — preserved as hex for downstream tooling.
    if len(payload) >= 20:
        md["echo_list_hex"] = payload[4:20].hex()
    if len(payload) >= 23:
        md["mac_tail_hex"] = payload[20:23].hex()

    return md


def _parse_gateway(payload: bytes) -> dict | None:
    """Gateway product: 4-byte payload (post-CID strip), magic `44 2F` already in CID."""
    md: dict = {"product": "gateway"}
    if len(payload) >= 3:
        md["mac_tail_hex"] = payload[1:4].hex()
    return md


def _signed_byte(b: int) -> int:
    return b - 256 if b >= 128 else b


@register_parser(
    name="mopeka",
    service_uuid=(MOPEKA_NRF52_UUID, MOPEKA_CC2540_UUID, MOPEKA_GATEWAY_UUID),
    description="Mopeka TankCheck propane / water tank level sensors",
    version="2.0.0",
    core=False,
)
class MopekaParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        payload = raw.manufacturer_payload
        if not payload:
            return None

        normalized = [u.lower() for u in (raw.service_uuids or [])]
        # Resolve which family by service UUID (16-bit short or 128-bit gateway).
        family = None
        if MOPEKA_NRF52_UUID in normalized or any(
            u.endswith("0000fee5-0000-1000-8000-00805f9b34fb") for u in normalized
        ):
            family = "nrf52"
        elif MOPEKA_CC2540_UUID in normalized or any(
            u.endswith("0000ada0-0000-1000-8000-00805f9b34fb") for u in normalized
        ):
            family = "cc2540"
        elif MOPEKA_GATEWAY_UUID in normalized:
            family = "gateway"
        else:
            # Fallback: best-effort guess from payload length.
            if len(payload) == 10:
                family = "nrf52"
            elif len(payload) >= 20:
                family = "cc2540"
            elif len(payload) <= 4:
                family = "gateway"
            else:
                return None

        if family == "nrf52":
            metadata = _parse_nrf52(payload)
        elif family == "cc2540":
            metadata = _parse_cc2540(payload)
        else:
            metadata = _parse_gateway(payload) or {}

        metadata["family"] = family

        # Identity prefers the in-payload 3-byte MAC tail when present.
        mac_tail = metadata.get("mac_tail_hex")
        if mac_tail:
            id_basis = f"mopeka:{mac_tail}"
        else:
            id_basis = f"{raw.mac_address}:mopeka"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="mopeka",
            beacon_type="mopeka",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
