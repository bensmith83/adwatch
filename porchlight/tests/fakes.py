"""Shared synthetic fixtures: a small field table and parser results."""

from datetime import datetime
from zoneinfo import ZoneInfo

from porchlight.resolver import FieldTable

TZ = ZoneInfo("UTC")
T0 = datetime(2026, 10, 19, 12, 0, tzinfo=TZ).timestamp()

TABLE = FieldTable.from_dict({
    "fields": [
        {"source": "meta", "parser": "watch", "key": "serial", "id_type": "Serial number", "confidence": "high",
         "vendor": "Acme", "product": "Watch", "mobility": "personal"},
        {"source": "meta", "parser": "speaker", "key": "device_id", "id_type": "Vendor device ID",
         "confidence": "high", "vendor": "Acme", "product": "Speaker", "mobility": "fixed"},
    ],
    "name_families": [], "unreliable_parsers": [],
    "rules": {"weak_bits": 24, "shared_if_concurrent_addresses": 3, "name_token_regex": "[0-9A-Fa-f]{4,}|\\d{3,}"},
})


def ad(t, addr="40:00:00:00:00:01", rssi=-60, name=None):
    return {"t": int(t * 1000), "addr": addr, "atype": "random", "rssi": rssi, "mfr": None, "svc": {},
            "uuids": [], "name": name, "tx": None}


def watch(serial="TEST0001"):
    return [{"parser": "watch", "beaconType": "watch", "deviceClass": "wearable", "stableKey": None,
             "metadata": {"serial": serial}}]
