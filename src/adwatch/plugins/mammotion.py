"""Mammotion (Agilexrobotics) robotic mower BLE advertisement parser.

Per apk-ble-hunting/reports/agilexrobotics-mammotion_passive.md. Company ID
0x01A8 (Alibaba / Tmall Genie AIS). Product ID (offset 2-5 of payload,
reversed) often ASCII-decodes to model code like HM430/MN232/PC100.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


MAMMOTION_COMPANY_ID = 0x01A8

_MAMMOTION_NAME_RE = re.compile(
    r"^(Luba|Yuka|Spino|RTK|RBSA|NB|Kumar-MK|SDPX|Ezy)", re.IGNORECASE
)


@register_parser(
    name="mammotion",
    company_id=MAMMOTION_COMPANY_ID,
    local_name_pattern=_MAMMOTION_NAME_RE.pattern,
    description="Mammotion (Luba/Yuka/Spino) robotic mowers",
    version="1.0.0",
    core=False,
)
class MammotionParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        has_company = (
            raw.manufacturer_data
            and len(raw.manufacturer_data) >= 2
            and int.from_bytes(raw.manufacturer_data[:2], "little") == MAMMOTION_COMPANY_ID
        )
        name = raw.local_name or ""
        name_match = bool(_MAMMOTION_NAME_RE.match(name))

        if not (has_company or name_match):
            return None

        metadata: dict = {}
        if name:
            metadata["device_name"] = name

        payload = raw.manufacturer_payload
        product_id_ascii = None
        if payload and len(payload) >= 6:
            version_id = payload[0] & 0x0F
            bluetooth_subtype = (payload[0] >> 4) & 0x0F
            metadata["version_id"] = version_id
            metadata["bluetooth_subtype"] = bluetooth_subtype
            if len(payload) >= 2:
                metadata["feature_mask"] = payload[1]
            # Product ID: 4 bytes at offset 2-5, reversed; often ASCII.
            pid_bytes = payload[2:6][::-1]
            try:
                ascii_pid = pid_bytes.decode("ascii")
                if all(c.isprintable() for c in ascii_pid):
                    product_id_ascii = ascii_pid
                    metadata["product_id"] = ascii_pid
            except UnicodeDecodeError:
                pass
            metadata["product_id_hex"] = pid_bytes.hex()
            # MAC address at offsets 6-11 for subtypes 0x8/0xA, 4-9 for subtype 0x9.
            if bluetooth_subtype in (0x8, 0xA) and len(payload) >= 12:
                mac_bytes = payload[6:12][::-1]
                metadata["broadcast_mac"] = ":".join(f"{b:02X}" for b in mac_bytes)
            elif bluetooth_subtype == 0x9 and len(payload) >= 10:
                mac_bytes = payload[4:10][::-1]
                metadata["broadcast_mac"] = ":".join(f"{b:02X}" for b in mac_bytes)

        if product_id_ascii:
            id_basis = f"mammotion:{product_id_ascii}:{metadata.get('broadcast_mac', raw.mac_address)}"
        else:
            id_basis = f"mammotion:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="mammotion",
            beacon_type="mammotion",
            device_class="mower",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex() if payload else "",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
