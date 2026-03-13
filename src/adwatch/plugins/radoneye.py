"""RadonEye RD200 radon detector plugin."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


@register_parser(
    name="radoneye",
    local_name_pattern=r"^FR:",
    description="RadonEye RD200 radon detector",
    version="1.0.0",
    core=False,
)
class RadonEyeParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        local_name = raw.local_name or ""
        if not local_name.startswith("FR:"):
            return None

        suffix = local_name[3:]  # After "FR:"
        metadata: dict = {"prefix": suffix[:2] if len(suffix) >= 2 else suffix}

        if suffix.startswith("R2"):
            metadata["version"] = "V1"
        elif suffix.startswith("RU") or suffix.startswith("RE"):
            metadata["version"] = "V2"
        else:
            metadata["version"] = "Unknown"

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:{local_name}".encode()
        ).hexdigest()[:16]

        payload = raw.manufacturer_payload
        raw_hex = payload.hex() if payload else ""

        return ParseResult(
            parser_name="radoneye",
            beacon_type="radoneye",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )

    def storage_schema(self):
        return None
