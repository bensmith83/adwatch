"""Ruuvi BLE advertisement parser (RAWv1/RAWv2/C5 + RuuviTag Air E0/E1/F0/6).

Decoders follow the Ruuvi Station app's own classes
(com/ruuvi/station/bluetooth/decoder/DecodeFormat*.java; apk-ble-hunting
ruuvi-station_passive.md). The app locates ``FF 99 04`` in the raw record and
indexes from the next byte (the data-format byte) == manufacturer_payload[0].

Units kept from the original plugin: temperature C, humidity %RH, pressure Pa,
acceleration mg, voltage mV. Sentinel/invalid values are omitted.

Identity: RAWv2 in-payload MAC (offset 18-23) when present, else BLE MAC.
Eddystone-URL mode (formats 2/4) is left to the eddystone plugin.
"""

import hashlib
import math
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

RUUVI_COMPANY_ID = 0x0499
RAWV2_FORMAT = 0x05
MIN_PAYLOAD_LEN = 18  # format(1) + fields(17) without MAC


def _u16(p, o):
    return (p[o] << 8) | p[o + 1]


def _s16(p, o):
    return struct.unpack_from(">h", p, o)[0]


def _power(meta, power_info):
    batt = power_info >> 5
    tx = power_info & 0x1F
    if batt != 2047:
        meta["voltage"] = batt + 1600
    if tx != 31:
        meta["tx_power"] = tx * 2 - 40


def _thp(meta, p, signed_hum=False):
    t = _s16(p, 1)
    if t != -32768:
        meta["temperature"] = t * 0.005
    h = _s16(p, 3) if signed_hum else _u16(p, 3)
    if h != 0xFFFF:
        meta["humidity"] = h * 0.0025
    pr = _u16(p, 5)
    if pr != 0xFFFF:
        meta["pressure"] = pr + 50000


def _decode_5(p):
    if len(p) < MIN_PAYLOAD_LEN:
        return None
    m = {}
    _thp(m, p)
    for name, off in (("accel_x", 7), ("accel_y", 9), ("accel_z", 11)):
        v = _s16(p, off)
        if v != -32768:
            m[name] = v
    _power(m, _u16(p, 13))
    m["movement_counter"] = p[15]
    m["measurement_sequence"] = _u16(p, 16)
    return m


def _decode_3(p):
    if len(p) < 14:
        return None
    temp = (p[2] & 0x7F) + struct.unpack_from("b", p, 3)[0] / 100.0
    if p[2] & 0x80:
        temp = -temp
    return {
        "humidity": p[1] / 2.0,
        "temperature": round(temp, 2),
        "pressure": p[4] * 256 + 50000 + p[5],
        "accel_x": _s16(p, 6),
        "accel_y": _s16(p, 8),
        "accel_z": _s16(p, 10),
        "voltage": _u16(p, 12),
    }


def _decode_c5(p):
    if len(p) < 12:
        return None
    m = {}
    _thp(m, p)
    _power(m, _u16(p, 7))
    m["movement_counter"] = p[9]
    m["measurement_sequence"] = _u16(p, 10)
    return m


def _decode_e0(p):
    if len(p) < 28:
        return None
    m = {}
    _thp(m, p, signed_hum=True)
    m.update({
        "pm1_0": round(_u16(p, 7) / 10, 2),
        "pm2_5": round(_u16(p, 9) / 10, 2),
        "pm4_0": round(_u16(p, 11) / 10, 2),
        "pm10": round(_u16(p, 13) / 10, 2),
        "co2": _u16(p, 15),
        "voc": ((p[17] & 1) << 8) | p[18],
        "nox": ((p[19] & 1) << 8) | p[20],
        "luminosity": _u16(p, 21),
        "sound_dba_avg": p[23] / 2,
        "sound_dba_peak": p[24] / 2,
        "measurement_sequence": _u16(p, 25),
        "voltage": p[27] * 30,
    })
    return m


def _decode_e1(p):
    if len(p) < 29:
        return None
    flags = p[28]
    bit = lambda n: (flags >> n) & 1  # noqa: E731
    m = {}
    _thp(m, p)
    m.update({
        "pm1_0": round(_u16(p, 7) / 10, 1),
        "pm2_5": round(_u16(p, 9) / 10, 1),
        "pm4_0": round(_u16(p, 11) / 10, 1),
        "pm10": round(_u16(p, 13) / 10, 1),
        "co2": _u16(p, 15),
        "voc": (p[17] << 1) | bit(6),
        "nox": (p[18] << 1) | bit(7),
        "luminosity": round(int.from_bytes(p[19:22], "big") / 100.0, 2),
        "sound_dba_inst": round(((p[22] << 1) | bit(3)) / 5 + 18, 2),
        "sound_dba_avg": round(((p[23] << 1) | bit(4)) / 5 + 18, 2),
        "sound_dba_peak": round(((p[24] << 1) | bit(5)) / 5 + 18, 2),
        "measurement_sequence": int.from_bytes(p[25:28], "big"),
    })
    return m


def _log_f0(enc, base):
    return 10 ** (enc / (254 / math.log10(base))) - 1


def _decode_f0(p):
    if len(p) < 13:
        return None
    return {
        "temperature": struct.unpack_from("b", p, 1)[0],
        "humidity": p[2] / 2.0,
        "pressure": p[3] * 100 + 90000,
        "pm1_0": round(_log_f0(p[4], 1001), 2),
        "pm2_5": round(_log_f0(p[5], 1001), 2),
        "pm4_0": round(_log_f0(p[6], 1001), 2),
        "pm10": round(_log_f0(p[7], 1001), 2),
        "co2": int(math.floor(_log_f0(p[8], 40001) + 0.5)),
        "voc": int(math.floor(_log_f0(p[9], 501) + 0.5)) + 1,
        "nox": int(math.floor(_log_f0(p[10], 501) + 0.5)) + 1,
        "luminosity": _log_f0(p[11], 40001),
        "sound_dba_avg": p[12] / 2,
    }


def _decode_6(p):
    if len(p) < 17:
        return None
    flags = p[16]
    bit = lambda n: (flags >> n) & 1  # noqa: E731
    m = {}
    _thp(m, p, signed_hum=True)
    m.update({
        "pm2_5": round(_u16(p, 7) / 10, 1),
        "co2": _u16(p, 9),
        "voc": (p[11] << 1) | bit(6),
        "nox": (p[12] << 1) | bit(7),
        "luminosity": float(math.floor(math.exp(p[13] * math.log(65536) / 254) + 0.5) - 1),
        "sound_dba_avg": round(((p[14] << 1) | bit(4)) / 5 + 18, 2),
        "measurement_sequence": p[15],
    })
    return m


DECODERS = {
    0x03: _decode_3,
    0x05: _decode_5,
    0x06: _decode_6,
    0xC5: _decode_c5,
    0xE0: _decode_e0,
    0xE1: _decode_e1,
    0xF0: _decode_f0,
}


@register_parser(
    name="ruuvi",
    company_id=RUUVI_COMPANY_ID,
    description="Ruuvi RAWv1/RAWv2/C5 + RuuviTag Air (E0/E1/F0/6)",
    version="1.1.0",
    core=False,
)
class RuuviParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 2:
            return None

        company_id = int.from_bytes(raw.manufacturer_data[:2], "little")
        if company_id != RUUVI_COMPANY_ID:
            return None

        payload = raw.manufacturer_data[2:]
        if not payload:
            return None

        decoder = DECODERS.get(payload[0])
        if decoder is None:
            return None
        try:
            metadata = decoder(payload)
        except (struct.error, IndexError):
            return None
        if metadata is None:
            return None
        metadata = {"data_format": payload[0], **metadata}

        # RAWv2: tag MAC in-clear at payload bytes 18-23
        if payload[0] == RAWV2_FORMAT and len(payload) >= 24:
            mac_str = ":".join(f"{b:02X}" for b in payload[18:24])
            id_hash = hashlib.sha256(mac_str.encode()).hexdigest()[:16]
        else:
            id_hash = hashlib.sha256(raw.mac_address.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="ruuvi",
            beacon_type="ruuvi",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata=metadata,
        )
