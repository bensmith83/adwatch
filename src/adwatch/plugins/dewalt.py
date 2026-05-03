"""DeWalt Tool Connect plugin.

Per apk-ble-hunting/reports/dewalt-toolconnect_passive.md:

  - Service UUID 0xFACE (DeWalt Tool Connect data service).
  - Manufacturer-data starts with `FE 00` (DeWalt-proprietary, NOT a SIG
    company ID). The framework treats `FE 00` as company_id 0x00FE LE.
  - Bytes 0-1 of mfr-data = `FE 00`; byte 2 = division ID; battery
    sub-layout exposes SoC %, temperature, voltage, charging state,
    anti-theft / pairing-mode flags.

  Rich plaintext jobsite telemetry — every battery broadcasts SoC + temp
  + voltage continuously while powered.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


DEWALT_SERVICE_UUID = "face"
# `FE 00` interpreted as little-endian 2-byte company_id.
DEWALT_COMPANY_ID = 0x00FE

DIVISION_NAMES = {
    0x00: "battery",
    0x01: "light",
    0x03: "drill",
    0x08: "compact_light",
    0xFE: "drill_alt",
}

STATUS_LSB_BITS = [
    "discharging", "disabled_by_delay", "soc_pushed", "warning_timeout",
    "firmware_pack_enabled", "enabled", "disabled_by_loan", "disabled_by_tether",
]
STATUS_MSB_BITS = [
    "commissioned", "tethered", "low_charge", "over_temp",
    "fully_charged", "is_charging", "app_pack_enabled", "is_loaned",
]


def _unpack_bits(byte: int, names: list[str]) -> dict[str, bool]:
    return {name: bool((byte >> i) & 0x01) for i, name in enumerate(names)}


def _decode_battery(payload: bytes) -> dict:
    """Decode the battery sub-layout. `payload` is the post-CID 20-byte block.

    Per the report (mfr-data offsets shown — subtract 2 for our payload[]):
      - mfr[2]=division (=0x00) → payload[0]
      - mfr[9]=SoC          → payload[7]
      - mfr[10]=status LSB  → payload[8]
      - mfr[11]=status MSB  → payload[9]
      - mfr[13]=firmware    → payload[11]
      - mfr[14]=temperature → payload[12]
      - mfr[15]=voltage     → payload[13]
      - mfr[16]=usage       → payload[14]
      - mfr[18]=impedance   → payload[16]
      - mfr[19,20]=capacity → payload[17:19]
      - mfr[21]=v-health    → payload[19]
      - PTI = (mfr[18] mfr[19] mfr[11]) BE → (payload[16] payload[17] payload[9])
    """
    md: dict = {}
    if len(payload) >= 8:
        soc_byte = payload[7]
        soc_steps = (soc_byte >> 4) & 0x0F  # 0..15
        md["soc_steps"] = soc_steps
        md["soc_percent"] = round(soc_steps * (100.0 / 15.0), 1)
        md["led_count"] = soc_byte & 0x03
    if len(payload) >= 10:
        md["status_lsb"] = _unpack_bits(payload[8], STATUS_LSB_BITS)
        md["status_msb"] = _unpack_bits(payload[9], STATUS_MSB_BITS)
    if len(payload) >= 12:
        fw = payload[11]
        md["firmware_major"] = (fw & 0xE0) >> 5
        md["firmware_minor"] = fw & 0x1F
    if len(payload) >= 13:
        md["temperature_c"] = payload[12] - 40
    if len(payload) >= 14:
        md["voltage_v"] = round(payload[13] / 10.0, 2)
    if len(payload) >= 15:
        md["usage_coulombs_raw"] = payload[14]
    if len(payload) >= 17:
        md["impedance_raw"] = payload[16]
    if len(payload) >= 19:
        md["capacity_raw"] = (payload[17] << 8) | payload[18]
    if len(payload) >= 20:
        md["voltage_health_raw"] = payload[19]
    # PTI (Product Type Index): big-endian uint24 from (mfr[18], mfr[19], mfr[11])
    if len(payload) >= 18:
        pti = (payload[16] << 16) | (payload[17] << 8) | payload[9]
        md["pti"] = pti
        md["pti_hex"] = f"{pti:06x}"
    return md


@register_parser(
    name="dewalt",
    company_id=DEWALT_COMPANY_ID,
    service_uuid=DEWALT_SERVICE_UUID,
    description="DeWalt Tool Connect (batteries, drills, lights, lasers)",
    version="1.0.0",
    core=False,
)
class DewaltParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        payload = raw.manufacturer_payload
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        uuid_hit = (
            DEWALT_SERVICE_UUID in normalized
            or any(u.endswith("0000face-0000-1000-8000-00805f9b34fb") for u in normalized)
        )
        cid_hit = raw.company_id == DEWALT_COMPANY_ID

        if not (uuid_hit or cid_hit):
            return None

        metadata: dict = {}

        if payload and len(payload) >= 1:
            div = payload[0]
            metadata["division_id"] = div
            metadata["division"] = DIVISION_NAMES.get(div, f"unknown_{div}")

            if div == 0x00:
                metadata.update(_decode_battery(payload))

        id_hash = hashlib.sha256(f"dewalt:{raw.mac_address}".encode()).hexdigest()[:16]
        raw_hex = payload.hex() if payload else ""

        return ParseResult(
            parser_name="dewalt",
            beacon_type="dewalt",
            device_class="power_tool",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )

    def storage_schema(self):
        return None
