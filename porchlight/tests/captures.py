"""Synthetic captures in real payload formats, with fake identifiers.

Every value here is made up (C0:FF:EE / 5C:FF:EE addresses, TEST serials,
c0ffee device IDs). Formats: Sonos manufacturer frames, Tesla's hashed-VIN
name on SIG 0x1122, WHOOP's serial name with heart-rate 0x180D, Shokz's
0x0CAC token.
"""

from __future__ import annotations

import json
from pathlib import Path

SIG = "-0000-1000-8000-00805f9b34fb"


def sonos(device_id: str, suffix: str):
    def make(t, addr, rssi):
        mfr = "a705" + "060012202a00ca00000800000000000000" + device_id + "123456"
        return {"t": t, "addr": addr, "atype": "random", "rssi": rssi, "mfr": mfr, "svc": {}, "uuids": [],
                "name": f"S39 {suffix} LE", "tx": None}
    return make


def tesla(vin_hash16: str):
    def make(t, addr, rssi):
        return {"t": t, "addr": addr, "atype": "random", "rssi": rssi, "mfr": None, "svc": {},
                "uuids": ["00001122" + SIG], "name": f"S{vin_hash16}C", "tx": None}
    return make


def whoop(serial: str):
    def make(t, addr, rssi):
        return {"t": t, "addr": addr, "atype": "random", "rssi": rssi, "mfr": None, "svc": {},
                "uuids": ["0000180d" + SIG], "name": f"WHOOP {serial}", "tx": None}
    return make


def shokz(token: str):
    def make(t, addr, rssi):
        return {"t": t, "addr": addr, "atype": "random", "rssi": rssi, "mfr": "ac0c" + token, "svc": {},
                "uuids": [], "name": None, "tx": None}
    return make


def rotating(prefix: str, every_s: float = 900.0):
    """A resolvable private address that changes every `every_s` seconds."""
    def addr(t_s: float) -> str:
        n = int(t_s // every_s) & 0xFFFF
        return f"{prefix}:{n >> 8:02X}:{n & 0xFF:02X}"
    return addr


def fixed(addr: str):
    return lambda t_s: addr


def stay(make, start: float, seconds: float, every: float, rssi: int, addr) -> list[dict]:
    out, t = [], start
    while t <= start + seconds:
        out.append(make(int(t * 1000), addr(t), rssi))
        t += every
    return out


def write(path: Path, *streams) -> Path:
    ads = sorted((a for s in streams for a in s), key=lambda a: a["t"])
    path.write_text("".join(json.dumps(a) + "\n" for a in ads))
    return path
