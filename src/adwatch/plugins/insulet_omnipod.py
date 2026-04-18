"""Insulet Omnipod 5 PDM BLE advertisement parser.

Per apk-ble-hunting/reports/insulet-myblue-pdm_passive.md. The PDM uses the
TWI SDK with dynamically-resolved company ID and byte offsets — byte layout
not recoverable from Java. Detect presence via name only.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


@register_parser(
    name="insulet_omnipod",
    local_name_pattern=r"(?i)^Omnipod|^PDM|^Insulet",
    description="Insulet Omnipod 5 insulin pump",
    version="1.0.0",
    core=False,
)
class InsuletOmnipodParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        name = raw.local_name or ""
        if not (name.lower().startswith("omnipod")
                or name.lower().startswith("pdm")
                or name.lower().startswith("insulet")):
            return None

        metadata: dict = {"device_name": name}
        id_hash = hashlib.sha256(f"omnipod:{raw.mac_address}".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="insulet_omnipod",
            beacon_type="insulet_omnipod",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )
