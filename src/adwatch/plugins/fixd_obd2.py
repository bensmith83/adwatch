"""FIXD Automotive OBD-II BLE scanner plugin.

The FIXD companion app identifies dongles purely by MAC-address prefix — the
advertisement itself carries no FIXD-specific fields (the dongle is a generic
Viecar/Seto/etc. OBD-II adapter). Prefix table per
apk-ble-hunting/reports/fixdapp-two_passive.md (SensorModel.java:20-23).
"""

import hashlib

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import register_parser


FIXD_SERVICE_UUID = "fff0"          # generic LiteOn-family OBD UUID; not FIXD-exclusive
FIXD_NAME = "FIXD"

# (mac_prefix, SensorModel) — checked in order; first match wins.
MAC_PREFIX_MODELS = (
    ("00:0D:18:00:00:01", "OLD_KICKSTARTER"),  # single prototype, exact MAC
    ("00:11:67:11",       "SETOSMART"),
    ("00:19:5D:F4",       "SETOSMART"),
    ("88:1B:99",          "VIECAR"),
    ("8C:DE:52",          "VIECAR"),
    ("34:81:F4",          "VIECAR"),
    ("66:1B:11",          "VIECAR_V2"),        # locally-administered
)

_MAC_PREFIXES = tuple(p for p, _ in MAC_PREFIX_MODELS)


def _classify_mac(mac: str) -> str | None:
    up = mac.upper()
    for prefix, model in MAC_PREFIX_MODELS:
        if up.startswith(prefix):
            return model
    return None


@register_parser(
    name="fixd_obd2",
    mac_prefix=_MAC_PREFIXES,
    local_name_pattern=r"^FIXD$",
    description="FIXD automotive OBD-II scanner",
    version="1.1.0",
    core=False,
)
class FixdObd2Parser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        sensor_model = _classify_mac(raw.mac_address)
        name_match = raw.local_name == FIXD_NAME

        if sensor_model is None and not name_match:
            return None

        metadata: dict = {}
        if raw.local_name:
            metadata["device_name"] = raw.local_name
        if sensor_model:
            metadata["sensor_model"] = sensor_model
        if raw.service_uuids and any("fff0" in u.lower() for u in raw.service_uuids):
            metadata["has_obd_service"] = True

        id_hash = hashlib.sha256(raw.mac_address.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="fixd_obd2",
            beacon_type="fixd_obd2",
            device_class="automotive",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
