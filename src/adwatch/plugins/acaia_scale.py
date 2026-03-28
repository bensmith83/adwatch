"""Acaia coffee scale BLE plugin."""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

_PATTERN = re.compile(r"(?i)^(ACAIA|LUNAR|PEARL|PYXIS|CINCO)")

_MODELS = {
    "pearls": "Pearl S",
    "pearl": "Pearl",
    "lunar": "Lunar",
    "pyxis": "Pyxis",
    "cinco": "Cinco",
    "acaia": "Acaia",
}


@register_parser(
    name="acaia_scale",
    local_name_pattern=r"(?i)^(ACAIA|LUNAR|PEARL|PYXIS|CINCO)",
    description="Acaia coffee scale advertisements",
    version="1.0.0",
    core=False,
)
class AcaiaScaleParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        local_name = getattr(raw, "local_name", None)
        if not local_name or not _PATTERN.match(local_name):
            return None

        # Model detection - check PEARLS before PEARL
        name_lower = local_name.lower()
        model = "Acaia"
        for prefix, model_name in _MODELS.items():
            if name_lower.startswith(prefix):
                model = model_name
                break

        # Device ID: extract after underscore or space separator
        device_id = None
        for sep in ("_", " "):
            if sep in local_name:
                device_id = local_name.split(sep, 1)[1]
                break

        metadata = {
            "model": model,
            "local_name": local_name,
        }
        if device_id is not None:
            metadata["device_id"] = device_id

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:acaia_scale".encode()
        ).hexdigest()[:16]

        raw_hex = raw.manufacturer_data.hex() if raw.manufacturer_data else ""

        return ParseResult(
            parser_name="acaia_scale",
            beacon_type="acaia_scale",
            device_class="scale",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )

    def storage_schema(self):
        return None
