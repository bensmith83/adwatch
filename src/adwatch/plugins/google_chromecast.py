"""Google Chromecast/Home BLE advertisement plugin."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

CHROMECAST_SERVICE_UUID = "fe2c"


@register_parser(
    name="google_chromecast",
    service_uuid=CHROMECAST_SERVICE_UUID,
    description="Google Chromecast/Home advertisements",
    version="1.0.0",
    core=False,
)
class GoogleChromecastParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        data = None

        # Check service_data for fe2c key
        if raw.service_data and CHROMECAST_SERVICE_UUID in raw.service_data:
            data = raw.service_data[CHROMECAST_SERVICE_UUID]
        # Fallback: check service_uuids for full UUID containing fe2c
        elif hasattr(raw, "service_uuids") and raw.service_uuids:
            if any(u.lower() == "fe2c" or u.lower() == "0000fe2c-0000-1000-8000-00805f9b34fb" for u in raw.service_uuids):
                data = b""
        else:
            return None

        if data is None:
            return None

        metadata = {}

        if len(data) >= 2:
            metadata["version"] = data[0]
            metadata["device_type"] = data[1]
            metadata["device_type_name"] = "Chromecast" if data[1] == 0x30 else "Google Home"

        if len(data) >= 5:
            metadata["flags_hex"] = data[2:5].hex()

        if len(data) >= 9:
            metadata["device_id_hex"] = data[5:9].hex()

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:google_chromecast".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="google_chromecast",
            beacon_type="google_chromecast",
            device_class="media",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex() if data else "",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
