"""GE Appliances BLE plugin.

Parses manufacturer data from GE Profile appliances (refrigerators, etc.).
Company ID 0x0929, MAC OUI FC:B9:7E.

Two ad variants observed:
  - Short (13 bytes): company_id(2) + variant(1) + status(1) + padding(9)
  - Long  (25 bytes): company_id(2) + variant(1) + status(1) + model(null-term) + padding
"""

import hashlib

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import register_parser

GE_COMPANY_ID = 0x0929


@register_parser(
    name="ge_appliances",
    company_id=GE_COMPANY_ID,
    description="GE Appliances (Profile refrigerators, etc.)",
    version="1.0.0",
    core=False,
)
class GEAppliancesParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        data = raw.manufacturer_data
        if not data or len(data) < 4:
            return None

        company_id = int.from_bytes(data[:2], "little")
        if company_id != GE_COMPANY_ID:
            return None

        ad_variant = data[2]
        status_byte = data[3]

        # Extract model from long ads (null-terminated ASCII after byte 3)
        model = None
        if len(data) > 4:
            model_bytes = data[4:]
            null_idx = model_bytes.find(0x00)
            if null_idx > 0:
                model = model_bytes[:null_idx].decode("ascii", errors="ignore")
                if not model.isprintable() or len(model) < 3:
                    model = None

        # Identity based on MAC (stable across ad variants)
        id_hash = hashlib.sha256(
            f"ge_appliances:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        subtype_names = {0xB1: "device_info", 0xB2: "idle"}
        metadata = {
            "ad_variant": ad_variant,
            "ad_subtype_name": subtype_names.get(ad_variant, "status"),
            "status_byte": status_byte,
        }
        if model:
            metadata["model"] = model

        return ParseResult(
            parser_name="ge_appliances",
            beacon_type="ge_appliances",
            device_class="smart_home",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata=metadata,
            stable_key=f"ge_appliances:{raw.mac_address}",
        )
