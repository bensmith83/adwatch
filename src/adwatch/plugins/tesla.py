"""Tesla vehicle phone-as-key BLE advertisement parser.

Per apk-ble-hunting/reports/teslamotors-tesla_passive.md. Tesla vehicles
advertise service UUID 0x1122 and a local name `S<two-char><model><VIN-hash>`.
Always-on beacon when the vehicle is parked — highly visible in parking areas.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


TESLA_SERVICE_UUID = "1122"

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

_TESLA_NAME_RE = re.compile(r"^S..([0-9A-Za-z]).*$")


@register_parser(
    name="tesla",
    service_uuid=TESLA_SERVICE_UUID,
    local_name_pattern=r"^S.{3,}$",
    description="Tesla vehicle phone-key advertisements",
    version="1.0.0",
    core=False,
)
class TeslaParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        has_uuid = any(
            u.lower() == TESLA_SERVICE_UUID
            for u in (raw.service_uuids or [])
        )
        name = raw.local_name or ""
        name_shape = bool(name.startswith("S") and len(name) >= 5)

        if not (has_uuid or name_shape):
            return None

        metadata: dict = {}
        if has_uuid:
            metadata["has_tesla_service_uuid"] = True
        if name:
            metadata["device_name"] = name
            m = _TESLA_NAME_RE.match(name)
            if m:
                model_char = m.group(1)
                metadata["model_char"] = model_char
                metadata["model"] = MODEL_CHAR_MAP.get(model_char, f"Unknown_{model_char}")
            # VIN-hash-derived identifier: the tail after position 3. Record as
            # an opaque persistent identifier.
            if len(name) >= 4:
                metadata["vin_hash_fragment"] = name[3:]

        if metadata.get("vin_hash_fragment"):
            id_basis = f"tesla:{metadata['vin_hash_fragment']}"
        else:
            id_basis = f"tesla:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="tesla",
            beacon_type="tesla",
            device_class="vehicle",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
