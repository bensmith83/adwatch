"""AliveCor KardiaMobile EKG BLE advertisement plugin."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

ALIVECOR_SERVICE_UUID = "021a9004-0382-4aea-bff4-6b3f1c5adfb4"


@register_parser(
    name="alivecor_ekg",
    service_uuid=ALIVECOR_SERVICE_UUID,
    local_name_pattern=r"^EKG-",
    description="AliveCor KardiaMobile EKG advertisements",
    version="1.0.0",
    core=False,
)
class AliveCorEkgParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        local_name = getattr(raw, "local_name", None)
        service_uuids = getattr(raw, "service_uuids", None) or []

        name_match = local_name and local_name.startswith("EKG-")
        uuid_match = ALIVECOR_SERVICE_UUID in service_uuids

        if not name_match and not uuid_match:
            return None

        metadata = {}
        if local_name:
            metadata["local_name"] = local_name
        if name_match:
            device_id = local_name[4:]  # everything after "EKG-"
            if device_id:
                metadata["device_id"] = device_id

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:alivecor_ekg".encode()
        ).hexdigest()[:16]

        raw_hex = raw.manufacturer_data.hex() if raw.manufacturer_data else ""

        return ParseResult(
            parser_name="alivecor_ekg",
            beacon_type="alivecor_ekg",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )

    def storage_schema(self):
        return None
