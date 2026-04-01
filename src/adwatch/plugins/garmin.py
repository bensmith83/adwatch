"""Garmin wearable BLE advertisement plugin."""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

GARMIN_COMPANY_ID = 0x0087


@register_parser(
    name="garmin",
    company_id=GARMIN_COMPANY_ID,
    description="Garmin wearable advertisements",
    version="1.0.0",
    core=False,
)
class GarminParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 3:
            return None

        company_id = int.from_bytes(raw.manufacturer_data[:2], "little")
        if company_id != GARMIN_COMPANY_ID:
            return None

        payload = raw.manufacturer_data[2:]
        if not payload:
            return None
        local_name = getattr(raw, "local_name", None) or ""

        # Device class based on local_name prefix
        if local_name.startswith("HRM-") or local_name.startswith("HRM "):
            device_class = "heart_rate_monitor"
        elif local_name.startswith("Edge"):
            device_class = "cycling_computer"
        elif local_name.startswith("Index"):
            device_class = "scale"
        else:
            device_class = "wearable"

        # Device family: first word (split on space or hyphen), capitalized
        if local_name:
            first_word = re.split(r"[\s\-]", local_name)[0]
            device_family = first_word[0].upper() + first_word[1:]
        else:
            device_family = "Unknown"

        model = local_name if local_name else "Unknown"

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:garmin".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="garmin",
            beacon_type="garmin",
            device_class=device_class,
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata={
                "device_family": device_family,
                "model": model,
                "message_type": payload[0],
            },
        )

    def storage_schema(self):
        return None
