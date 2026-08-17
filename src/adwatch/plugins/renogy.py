"""Renogy DC Home plugin — presence + model identification only.

Ground truth: apk-ble-hunting report ``renogy-dchome_passive.md``
(``com.renogy.dchome``, Stage 4b).

Renogy broadcasts **no passive telemetry**.  The app installs no ScanFilter and
parses no service data; discovery is entirely by BLE local-name prefix
(``q4/b.java:12,80-90`` plus the ~90-entry SKU catalog at
``ui/module/device/add/manual/o.java:11``).  Battery voltage, SoC, shunt
current, TPMS pressure and so on are Modbus reads over a connected GATT pipe,
never in the advertisement.

The one manufacturer-data decode in the whole app
(``MBlueBean.java:79-97 f()``) applies only to ``RTMShunt*`` devices and yields
a **model** ID, not live state: bytes 4..7 of the first manufacturer entry's
value, uppercase hex.  The app reads ``valueAt(0)`` blindly, so no company ID
is checked — the CID is recorded here for reference only.

Deliberately *not* claimed, despite appearing in Renogy's own prefix list:

* ``TPMS`` — already owned by ``plugins/tpms.py`` and used by many vendors.
* ``BT`` and ``A1`` — two-character prefixes that would match a large slice of
  all BLE devices.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

# Anchored, case-insensitive (q4/b.java matches prefixes case-insensitively).
RENOGY_NAME_PATTERN = (
    r"(?i)^("
    r"RTMShunt"
    r"|RNG-CTRL-|RNGSHUNT|RNGPMS|RNGUSBAT|RNGRBC"
    r"|RBC\d"
    r"|BTR(IC|IV|AC|I213|IL23)"
    r"|RCC\w"
    r"|RENOGY"
    r")"
)

_RENOGY_NAME_RE = re.compile(RENOGY_NAME_PATTERN)

# Name prefix (uppercase) -> (model SKU or None, product family).
_RAW_MODEL_PREFIXES = {
    "RNGUSBATP100": ("RBT12100LFP-SHBT", "battery"),
    "RNGSHUNT500": ("Shunt500", "shunt"),
    "RNGPMS1260": ("RSHCB-B02P-G1", "gateway"),
    "RENOGY FROSTBOX": ("Renogy FrostBox", "fridge"),
    "RTMSHUNT": ("Shunt300", "shunt"),
    "RNG-CTRL-": (None, "charge controller"),
    "RNGUSBAT": (None, "battery"),
    "RNGSHUNT": (None, "shunt"),
    "RNGRBC": (None, "dc-dc charger"),
    "RNGPMS": (None, "gateway"),
    "BTRI213": (None, "inverter"),
    "BTRIL23": (None, "inverter"),
    "BTRIC": (None, "inverter"),
    "BTRIV": (None, "inverter"),
    "BTRAC": (None, "inverter"),
    "RBC": (None, "dc-dc charger"),
    "RCC": (None, "charge controller"),
}

# Longest prefix first so specific SKUs beat the family fallbacks.
MODEL_PREFIXES = {
    k: _RAW_MODEL_PREFIXES[k]
    for k in sorted(_RAW_MODEL_PREFIXES, key=lambda p: (-len(p), p))
}

# MBlueBean.f() gates on this name prefix before reading bytes 4..7.
SHUNT_NAME_PREFIX = "RTMSHUNT"
MODEL_ID_SLICE = slice(4, 8)  # z8.c(4, 7) is an inclusive IntRange


@register_parser(
    name="renogy",
    local_name_pattern=RENOGY_NAME_PATTERN,
    description="Renogy solar controllers, batteries, inverters and shunts",
    version="1.0.0",
    core=False,
)
class RenogyParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        name = raw.local_name
        if not name or not _RENOGY_NAME_RE.search(name):
            return None

        upper = name.upper()
        metadata: dict = {
            "local_name": name,
            # All real data is behind a connected Modbus pipe.
            "telemetry": False,
        }

        model, family = self._catalog_lookup(upper)
        metadata["product_family"] = family
        if model:
            metadata["model"] = model

        payload = raw.manufacturer_payload or b""
        if raw.manufacturer_data and len(raw.manufacturer_data) >= 2:
            metadata["company_id"] = int.from_bytes(
                raw.manufacturer_data[:2], "little"
            )

        if upper.startswith(SHUNT_NAME_PREFIX) and len(payload) >= 8:
            # A per-model identifier shared by every unit of that model — not a
            # serial, so it must never anchor the identity hash.
            metadata["model_id"] = payload[MODEL_ID_SLICE].hex().upper()

        id_hash = hashlib.sha256(
            f"renogy:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="renogy",
            beacon_type="renogy",
            device_class="energy",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata=metadata,
        )

    @staticmethod
    def _catalog_lookup(upper_name: str):
        for prefix, entry in MODEL_PREFIXES.items():
            if upper_name.startswith(prefix):
                return entry
        return (None, "unknown")
