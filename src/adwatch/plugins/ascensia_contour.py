"""Ascensia Contour glucose meter BLE advertisement parser.

Per apk-ble-hunting/reports/ascensia-contour-us_passive.md. Company ID 0x0167
(Ascensia Diabetes Care) + name-prefix filter. No advertisement telemetry.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


ASCENSIA_COMPANY_ID = 0x0167


@register_parser(
    name="ascensia_contour",
    company_id=ASCENSIA_COMPANY_ID,
    local_name_pattern=r"^(Contour|Portal)",
    description="Ascensia Contour glucose meters",
    version="1.0.0",
    core=False,
)
class AscensiaContourParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        has_company = (
            raw.manufacturer_data
            and len(raw.manufacturer_data) >= 2
            and int.from_bytes(raw.manufacturer_data[:2], "little") == ASCENSIA_COMPANY_ID
        )
        name = raw.local_name or ""
        name_match = name.startswith("Contour") or name.startswith("Portal")

        if not (has_company or name_match):
            return None

        metadata: dict = {}
        if name:
            metadata["device_name"] = name

        id_hash = hashlib.sha256(f"ascensia:{raw.mac_address}".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="ascensia_contour",
            beacon_type="ascensia_contour",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_payload or b"").hex(),
            metadata=metadata,
        )
