"""Tesla BLE advertisement parser.

Two paths:

1. **Vehicle phone-key** (per `apk-ble-hunting/reports/teslamotors-tesla_passive.md`):
   service UUID 0x1122 + local name `S<two-char><model><VIN-hash>`. Always-on
   when the vehicle is parked — highly visible in parking lots.

2. **Non-vehicle Tesla product**: SIG company ID `0x022B` (Tesla, Inc.) in
   manufacturer data. The vehicle keys do NOT use mfr-data, so a CID match
   means a different Tesla product — Powerwall, Wall Connector, or another
   accessory. We tag `device_class="energy"` (Powerwall / Wall Connector are
   both energy products; closest fit) and stash `product_kind="non_vehicle"`
   in metadata until further captures pin it down.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import _normalize_uuid, register_parser


TESLA_SERVICE_UUID = "1122"
_TESLA_UUID_NORMALIZED = _normalize_uuid(TESLA_SERVICE_UUID)

# SIG-assigned company ID for "Tesla, Inc." — see `_bt_company_ids.py:0x022B`.
TESLA_COMPANY_ID = 0x022B

MODEL_CHAR_MAP = {
    "3": "Model 3",
    "Y": "Model Y",
    "S": "Model S",
    "X": "Model X",
    "C": "Compact/3/Y (variant C)",
    "R": "Roadster",
    "D": "Dual Motor S/X",
    "P": "Performance",
}

# Name shape: S + 2 chars + recognized model char + VIN-hash tail (≥4 chars).
# Restricting position 3 to the known model chars avoids false-positives on
# common S-prefixed device names (Samsung, Sonos, Surface, SPRK+, ...).
_TESLA_NAME_PATTERN = r"^S[A-Za-z0-9]{2}[3YSXCRDP][A-Za-z0-9]{4,}$"
_TESLA_NAME_RE = re.compile(_TESLA_NAME_PATTERN)


@register_parser(
    name="tesla",
    company_id=TESLA_COMPANY_ID,
    service_uuid=TESLA_SERVICE_UUID,
    local_name_pattern=_TESLA_NAME_PATTERN,
    description="Tesla vehicles + non-vehicle products (Powerwall / Wall Connector / accessory)",
    version="1.2.0",
    core=False,
)
class TeslaParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        has_uuid = any(
            _normalize_uuid(u) == _TESLA_UUID_NORMALIZED
            for u in (raw.service_uuids or [])
        )
        has_company = (
            raw.manufacturer_data
            and len(raw.manufacturer_data) >= 2
            and int.from_bytes(raw.manufacturer_data[:2], "little") == TESLA_COMPANY_ID
        )
        name = raw.local_name or ""
        name_match = _TESLA_NAME_RE.match(name)

        if not (has_uuid or name_match or has_company):
            return None

        # Vehicle path (UUID or vehicle-name regex) takes precedence over the
        # CID-only match — a Tesla vehicle that one day starts emitting
        # mfr-data is still a vehicle.
        is_vehicle = bool(has_uuid or name_match)

        metadata: dict = {}
        if has_uuid:
            metadata["has_tesla_service_uuid"] = True
        if name:
            metadata["device_name"] = name
        if name_match:
            model_char = name[3]
            metadata["model_char"] = model_char
            metadata["model"] = MODEL_CHAR_MAP.get(model_char, f"Unknown_{model_char}")
            metadata["vin_hash_fragment"] = name[3:]
        if has_company:
            metadata["company_id_hex"] = f"0x{TESLA_COMPANY_ID:04X}"
            if not is_vehicle:
                # No vehicle signal — likely Powerwall / Wall Connector / accessory.
                metadata["product_kind"] = "non_vehicle"

        if metadata.get("vin_hash_fragment"):
            id_basis = f"tesla:{metadata['vin_hash_fragment']}"
        else:
            id_basis = f"tesla:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="tesla",
            beacon_type="tesla",
            device_class="vehicle" if is_vehicle else "energy",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_payload or b"").hex() if has_company else "",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
