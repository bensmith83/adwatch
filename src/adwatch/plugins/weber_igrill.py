"""Weber iGrill BLE thermometer plugin."""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


@register_parser(
    name="weber_igrill",
    local_name_pattern=r"(?i)igrill",
    description="Weber iGrill thermometer advertisements",
    version="1.0.0",
    core=False,
)
class WeberIGrillParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        local_name = getattr(raw, "local_name", None)
        if not local_name or not re.search(r"igrill", local_name, re.IGNORECASE):
            return None

        # Model detection
        name_lower = local_name.lower()
        if "mini" in name_lower:
            model = "iGrill Mini"
            probes = 1
        elif "2" in name_lower:
            model = "iGrill 2"
            probes = 4
        elif "3" in name_lower:
            model = "iGrill 3"
            probes = 4
        else:
            model = "iGrill Unknown"
            probes = 4

        # Device ID: suffix after last underscore
        device_id = None
        if "_" in local_name:
            suffix = local_name.rsplit("_", 1)[1]
            # Only set device_id if suffix looks like a model variant won't confuse it
            if suffix and suffix.lower() not in ("mini", "unknown"):
                device_id = suffix

        metadata = {
            "model": model,
            "probes": probes,
            "local_name": local_name,
        }
        if device_id is not None:
            metadata["device_id"] = device_id

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:weber_igrill".encode()
        ).hexdigest()[:16]

        raw_hex = raw.manufacturer_data.hex() if raw.manufacturer_data else ""

        return ParseResult(
            parser_name="weber_igrill",
            beacon_type="weber_igrill",
            device_class="thermometer",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )

    def storage_schema(self):
        return None
