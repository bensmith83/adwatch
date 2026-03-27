"""Nordic Thingy:52 development kit plugin."""
import hashlib
from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

THINGY_UUID = "ef680100-9b35-4933-9b10-52ffa9740042"

@register_parser(
    name="nordic_thingy",
    service_uuid=THINGY_UUID,
    local_name_pattern=r"^Thingy",
    description="Nordic Thingy:52 dev kit",
    version="1.0.0",
    core=False,
)
class NordicThingyParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        # Must match on service UUID or local name
        has_uuid = (raw.service_uuids and THINGY_UUID in raw.service_uuids) or \
                   (raw.service_data and THINGY_UUID in raw.service_data)
        has_name = raw.local_name and raw.local_name.startswith("Thingy")
        if not has_uuid and not has_name:
            return None

        metadata = {}
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        # Extract random device ID from manufacturer data (Nordic company_id 0x0059)
        if raw.manufacturer_data and len(raw.manufacturer_data) >= 6:
            company_id = int.from_bytes(raw.manufacturer_data[:2], "little")
            if company_id == 0x0059:
                device_id_bytes = raw.manufacturer_data[2:6]
                metadata["random_device_id"] = device_id_bytes[::-1].hex()

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:nordic_thingy".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="nordic_thingy",
            beacon_type="nordic_thingy",
            device_class="dev_kit",
            identifier_hash=id_hash,
            raw_payload_hex=raw.manufacturer_data.hex() if raw.manufacturer_data else "",
            metadata=metadata,
        )
