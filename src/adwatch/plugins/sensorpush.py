"""SensorPush temperature/humidity/pressure sensor plugin.

Per apk-ble-hunting report cousins-sears-beaconthermometer_passive.md
(CSSensorService$2.onScanResult + res/raw/definitions.json).

The app reads the AD 0xFF value in full — there is no SIG company ID, so the
first two bytes adwatch treats as a "CID" are sensor data. All offsets below
index ``raw.manufacturer_data`` directly (== report ``mfg[N]``).

Families:
  * V2 (HTP.xw=64, HT.w=65, TC=66): mfg[0] = header; packet type = mfg[0] & 3
    (3 = device-id packet), device version = (mfg[0] >> 2) + 64.
      - data packet: mfg[1 : 1+bytesPerPackedSample] = LE mixed-radix packed sample
      - id packet:   mfg[1:5] LE uint32 device id; bit 31 = "not initialized"
  * HT1 (version 1): 4 or 7 bytes; mfg[3] bits 2-6 = version (==1), bit 7 =
    not-initialized; mfg[4:7] LE 24-bit device id (7-byte form). HT1 sample
    packing is legacy/encrypted in CSSample — exposed raw only.

Identity: in-payload device id when present (id packet / 7-byte HT1), else
MAC + local name (data packets carry no id; app correlates by MAC).
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

SENSORPUSH_NAME_RE = re.compile(r"^SensorPush")

# deviceVersion -> (name, bytesPerPackedSample, [(field, min, max, resolution)])
V2_MODELS = {
    64: ("HTP.xw", 6, [
        ("temperature_c", -40.0, 140.0, 0.0025),
        ("humidity", 0.0, 100.0, 0.0025),
        ("pressure_pa", 30000.0, 125000.0, 1.0),
    ]),
    65: ("HT.w", 4, [
        ("temperature_c", -40.0, 125.0, 0.0025),
        ("humidity", 0.0, 100.0, 0.0025),
    ]),
    66: ("TC", 2, [
        ("probe_temperature_c", -200.0, 1800.0, 0.0625),
    ]),
}


def _unpack(packed: int, params) -> dict:
    out = {}
    for name, lo, hi, res in params:
        steps = int(round(1 + (hi - lo) / res))
        out[name] = round(lo + (packed % steps) * res, 5)
        packed //= steps
    return out


def _decode_v2(mfg: bytes) -> dict | None:
    header = mfg[0]
    if header & 0x80:
        return None  # Java signed shift -> unsupported version
    version = (header >> 2) + 64
    model = V2_MODELS.get(version)
    if model is None:
        return None
    name, bps, params = model
    ptype = header & 3
    meta = {"model": name, "device_version": version}
    if ptype == 3:
        if len(mfg) < 5:
            return None
        word = int.from_bytes(mfg[1:5], "little")
        meta["packet_type"] = "device_id"
        meta["initialized"] = not bool(word & 0x80000000)
        meta["device_id"] = word & 0x7FFFFFFF
        return meta
    if len(mfg) != bps + 1:
        return None
    meta["packet_type"] = "data"
    meta.update(_unpack(int.from_bytes(mfg[1:1 + bps], "little"), params))
    if "pressure_pa" in meta:
        meta["pressure_hpa"] = round(meta["pressure_pa"] / 100.0, 2)
    return meta


def _decode_ht1(mfg: bytes) -> dict | None:
    if len(mfg) not in (4, 7):
        return None
    if ((mfg[3] & 0x7C) >> 2) != 1:
        return None
    meta = {
        "model": "HT1",
        "device_version": 1,
        "packet_type": "data",
        "initialized": not bool(mfg[3] & 0x80),
        "packed_sample_hex": mfg[0:4].hex(),
    }
    if len(mfg) == 7:
        meta["device_id"] = int.from_bytes(mfg[4:7], "little")
    return meta


@register_parser(
    name="sensorpush",
    local_name_pattern=r"^SensorPush",
    description="SensorPush HT1/HT.w/HTP.xw/TC temperature/humidity/pressure sensors",
    version="2.0.0",
    core=False,
)
class SensorPushParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.local_name or not SENSORPUSH_NAME_RE.match(raw.local_name):
            return None

        mfg = raw.manufacturer_data or b""
        meta: dict = {}
        if mfg:
            meta = _decode_v2(mfg) or _decode_ht1(mfg) or {}

        if "device_id" in meta:
            id_basis = f"sensorpush:{meta['device_id']}"
        else:
            id_basis = f"{raw.mac_address}:{raw.local_name}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="sensorpush",
            beacon_type="sensorpush",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=mfg.hex(),
            metadata=meta,
        )

    def storage_schema(self):
        return None
