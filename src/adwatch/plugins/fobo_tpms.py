"""FOBO Tire / FOBO Bike TPMS plugin (Salutica Allied Solutions).

Byte layouts per apk-ble-hunting/reports/salutica-fobotpms_passive.md.

FOBO valve-cap sensors beacon 24x7 with pressure / temperature / battery /
rotation in the clear. The app slices the raw ScanRecord by absolute offset:

    [0-2] flags AD  [3-6] 16-bit service-class AD (UUID LE at bytes 5-6)
    [7] len  [8] AD type  [9-10] CID (or 16-bit UUID)  [11..] payload

The app's FOBO-Link decoder uses ``slice = result[11:]`` which confirms the
telemetry element's post-header payload begins at raw byte 11. adwatch has
already split AD structures, so raw byte N == ``manufacturer_payload[N-11]``
(or the service-data value, which also excludes its 2-byte UUID).

Salutica holds SIG company ID 0x0127; OUI 00:15:88 is the Salutica MAC
prefix. Both are used as corroboration for the generic-looking 16-bit
family UUIDs (0x0126 / 0x0129 / 0x012B / 0x014A / 0x010A), never alone as
a registration on the OUI.
"""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


SALUTICA_COMPANY_ID = 0x0127
FOBO_OUI = "00:15:88"
FOBO_GATEWAY_NAME = "FOBO-GATEWAY"
APPLE_COMPANY_ID = 0x004C

# short UUID -> (family, wire format)
FOBO_FAMILIES = {
    "ee00": ("tire", "A"),
    "eefe": ("bike", "A"),
    "faf0": ("midget", "B"),
    "0126": ("new_midget", "B"),
    "0129": ("elite", "B"),
    "012b": ("next", "B"),
    "fcf0": ("next_beacon", "B25"),
    "014a": ("fobo_link", "C"),
    "010a": ("gateway", "D"),
}

# UUIDs not in the 0xExxx/0xFxxx vendor space look generic: require shape
# or Salutica corroboration (OUI / CID / gateway name) before claiming.
_WEAK_UUIDS = frozenset({"0126", "0129", "012b", "014a", "010a"})

_BT_SUFFIX = "-0000-1000-8000-00805f9b34fb"
FOBO_SERVICE_UUIDS = [f"0000{s}{_BT_SUFFIX}" for s in FOBO_FAMILIES]


def _short_uuid(u: str) -> str | None:
    u = u.lower()
    if len(u) == 4:
        return u
    if len(u) == 36 and u.startswith("0000") and u.endswith(_BT_SUFFIX):
        return u[4:8]
    return None


def _pressure(raw_counts: int) -> tuple[int, bool]:
    # App clamps <= 30 counts to 0 (deflated / absent tyre).
    if raw_counts <= 30:
        return 0, True
    return raw_counts, False


def decode_format_a(flags_byte: int, temp_byte: int, word: int) -> dict:
    """Classic sensor: raw byte 17 flags, 18 temp, 19-20 BE word."""
    pressure, deflated = _pressure(word & 0x3FF)
    return {
        "flags_nibble": flags_byte >> 4,
        "temperature_c": temp_byte - 50,
        "pressure_raw": pressure,
        "pressure_deflated": deflated,
        "battery_mv": ((word >> 10) & 0x3F) * 100,
    }


def decode_format_b(word1: int, word2: int, rotation_in_word2: bool = False) -> dict:
    """New sensor / FOBO-Link packing (two BE 16-bit words)."""
    pressure, deflated = _pressure(word2 & 0x7FF)
    if rotation_in_word2:
        rotating = bool((word2 >> 15) & 1)       # FOBO-Link mask form
    else:
        rotating = bool((word1 >> 14) & 1)       # word1 string-bit 1 (FAF0 path)
    return {
        "temperature_c": (word1 & 0x7F) - 40,
        "battery_mv": ((word1 >> 7) & 0x7F) * 10 + 2000,
        "pressure_raw": pressure,
        "pressure_deflated": deflated,
        "rotating": rotating,
    }


def decode_format_d(major: int, minor: int) -> dict:
    """In-car gateway first-discovery path (raw bytes 25-26 / 27-28)."""
    tire_id = (major >> 8) & 0x0F
    out: dict = {"tire_id": tire_id}
    no_reading = minor == 0xFFFF
    if no_reading:
        out["no_reading"] = True
    if tire_id == 0:
        out["display_battery_mv"] = 0 if no_reading else ((minor >> 10) & 0x3F) * 100
        return out
    if tire_id > 8:
        return out
    out["temperature_c"] = (major & 0xFF) - 50
    if tire_id <= 4:
        out["position"] = tire_id
        p = minor & 0x3FF
        batt = ((minor >> 10) & 0x3F) * 100
    else:
        out["position"] = tire_id - 4
        p = minor & 0x7FF
        batt = ((minor >> 11) & 0x1F) * 40 + 2000
    if no_reading:
        out["pressure_raw"] = 0
        out["battery_mv"] = 0
    else:
        out["pressure_raw"], out["pressure_deflated"] = _pressure(p)
        out["battery_mv"] = batt
    return out


@register_parser(
    name="fobo_tpms",
    company_id=SALUTICA_COMPANY_ID,
    service_uuid=FOBO_SERVICE_UUIDS,
    local_name_pattern=r"^FOBO-GATEWAY$",
    description="FOBO Tire / Bike TPMS sensors, FOBO-Link relay and gateway (Salutica)",
    version="1.0.0",
    core=False,
)
class FoboTpmsParser:
    def _family(self, raw: RawAdvertisement) -> str | None:
        candidates = list(raw.service_uuids or [])
        if raw.service_data:
            candidates += list(raw.service_data.keys())
        for u in candidates:
            s = _short_uuid(u)
            if s in FOBO_FAMILIES:
                return s
        return None

    def _segment(self, raw: RawAdvertisement, short: str | None) -> bytes:
        """Bytes starting at raw scan-record byte 11."""
        if raw.manufacturer_payload:
            return raw.manufacturer_payload
        if raw.service_data and short:
            for k, v in raw.service_data.items():
                if _short_uuid(k) == short and v:
                    return v
        return b""

    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        name = raw.local_name or ""
        mac = raw.mac_address.upper()
        oui_match = mac.startswith(FOBO_OUI)
        salutica_cid = raw.company_id == SALUTICA_COMPANY_ID
        is_gateway_name = name == FOBO_GATEWAY_NAME
        corroborated = oui_match or salutica_cid or is_gateway_name

        short = self._family(raw)
        if short is None and not (salutica_cid or is_gateway_name):
            return None

        seg = self._segment(raw, short)
        metadata: dict = {
            "oui_match": oui_match,
            "salutica_cid": salutica_cid,
        }
        if short is not None:
            family, fmt = FOBO_FAMILIES[short]
            metadata["service_uuid"] = short
        elif is_gateway_name:
            family, fmt = "gateway", None
        else:
            family, fmt = "unknown", None
        metadata["family"] = family
        if is_gateway_name:
            metadata["gateway_name"] = True

        decoded = False
        if fmt == "A" and len(seg) >= 10:
            metadata.update(decode_format_a(seg[6], seg[7], (seg[8] << 8) | seg[9]))
            decoded = True
        elif fmt == "B" and len(seg) >= 10:
            w1, w2 = struct.unpack(">HH", seg[6:10])
            metadata.update(decode_format_b(w1, w2))
            decoded = True
        elif fmt == "B25" and len(seg) >= 18:
            w1, w2 = struct.unpack(">HH", seg[14:18])
            metadata.update(decode_format_b(w1, w2))
            decoded = True
        elif fmt == "C" and len(seg) >= 11:
            count = 0
            for idx, base in ((1, 4), (2, 11)):
                if len(seg) < base + 7:
                    break
                wa, wb = struct.unpack(">HH", seg[base + 3:base + 7])
                metadata[f"sensor{idx}_id"] = "001588" + seg[base:base + 3].hex()
                for k, v in decode_format_b(wa, wb, rotation_in_word2=True).items():
                    metadata[f"sensor{idx}_{k}"] = v
                count += 1
            metadata["relay_sensor_count"] = count
            decoded = True
        elif fmt == "D":
            words = None
            mfr = raw.manufacturer_data or b""
            if (raw.company_id == APPLE_COMPANY_ID and len(mfr) >= 24
                    and mfr[2:4] == b"\x02\x15"):
                words = mfr[20:24]            # iBeacon major/minor (raw 25-28)
            elif len(seg) >= 18:
                words = seg[14:18]
            if words is not None:
                major, minor = struct.unpack(">HH", words)
                metadata.update(decode_format_d(major, minor))
                decoded = True

        if decoded and fmt:
            metadata["wire_format"] = "B" if fmt == "B25" else fmt

        if short in _WEAK_UUIDS and not (decoded or corroborated):
            return None

        if oui_match:
            sensor_id = "001588" + mac.replace(":", "")[6:].lower()
            metadata["sensor_id"] = sensor_id
            basis = f"fobo:{sensor_id}"
        else:
            basis = f"fobo:{raw.mac_address}:{family}"
        id_hash = hashlib.sha256(basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="fobo_tpms",
            beacon_type="fobo_tpms",
            device_class="gateway" if family in ("gateway", "fobo_link") else "sensor",
            identifier_hash=id_hash,
            raw_payload_hex=seg.hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
