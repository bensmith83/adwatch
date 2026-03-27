"""HP Printer BLE presence plugin."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

HP_COMPANY_ID = 0x0434
HP_UUIDS = ["fdf7", "fe77", "fe78"]


@register_parser(
    name="hp_printer",
    company_id=HP_COMPANY_ID,
    service_uuid=HP_UUIDS,
    description="HP Printers",
    version="1.0.0",
    core=False,
)
class HPPrinterParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        matched = False
        if raw.manufacturer_data and len(raw.manufacturer_data) >= 2:
            cid = int.from_bytes(raw.manufacturer_data[:2], "little")
            if cid == HP_COMPANY_ID:
                matched = True
        if not matched:
            for uuid in HP_UUIDS:
                if (raw.service_uuids and uuid in raw.service_uuids) or \
                   (raw.service_data and uuid in raw.service_data):
                    matched = True
                    break
        if not matched:
            return None

        metadata = {}
        if raw.local_name:
            metadata["printer_model"] = raw.local_name

        payload_hex = ""
        if raw.manufacturer_data and len(raw.manufacturer_data) > 2:
            payload_hex = raw.manufacturer_data[2:].hex()

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:hp_printer".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="hp_printer",
            beacon_type="hp_printer",
            device_class="printer",
            identifier_hash=id_hash,
            raw_payload_hex=payload_hex,
            metadata=metadata,
        )
