"""Masimo MightySat pulse oximeter BLE advertisement parser.

Per apk-ble-hunting/reports/masimo-merlin-consumer_passive.md. Company ID
0x0243 + name filter. Byte offsets inside mfr data are obfuscated in the
companion APK — not decoded here.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


MASIMO_COMPANY_ID = 0x0243


@register_parser(
    name="masimo",
    company_id=MASIMO_COMPANY_ID,
    local_name_pattern=r"(?i)^(MightySat|Masimo)",
    description="Masimo MightySat pulse oximeter",
    version="1.0.0",
    core=False,
)
class MasimoParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        has_company = (
            raw.manufacturer_data
            and len(raw.manufacturer_data) >= 2
            and int.from_bytes(raw.manufacturer_data[:2], "little") == MASIMO_COMPANY_ID
        )
        name = raw.local_name or ""
        name_match = name.lower().startswith(("mightysat", "masimo"))

        if not (has_company or name_match):
            return None

        metadata: dict = {}
        if name:
            metadata["device_name"] = name
        payload = raw.manufacturer_payload
        if payload:
            metadata["protocol_version"] = payload[0]
            metadata["payload_hex"] = payload.hex()

        id_hash = hashlib.sha256(f"masimo:{raw.mac_address}".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="masimo",
            beacon_type="masimo",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex=(payload or b"").hex(),
            metadata=metadata,
        )
