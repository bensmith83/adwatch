"""Maytronics Dolphin pool cleaner BLE advertisement parser.

Per apk-ble-hunting/reports/maytronics-app_passive.md. Multiple detection
paths — name patterns (IoT_PWS / maytronics00 / may / MxX_pws / bare serials)
and a 6-byte mfr-data layout with model/protocol/serial-hash/MU-version.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


_MAYTRONICS_NAME_RE = re.compile(
    r"^(IoT_PWS|maytronics00|may|[Mm][A-Za-z0-9]_(?:PWS|pws)|[A-Za-z0-9]{8}$|[0-9a-fA-F]{12}$)"
)


MODEL_CODES = {
    0x6C: "Dolphin M-series",
    0x66: "Dolphin legacy",
}


@register_parser(
    name="maytronics",
    local_name_pattern=_MAYTRONICS_NAME_RE.pattern,
    description="Maytronics Dolphin robotic pool cleaners",
    version="1.0.0",
    core=False,
)
class MaytronicsParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        name = raw.local_name or ""
        name_match = bool(_MAYTRONICS_NAME_RE.match(name))

        # 6-byte mfr-data payload (after stripping 2-byte company id):
        # [model][proto_ver][skip][serial_hash_lo][serial_hash_hi][mu_ver]
        payload = raw.manufacturer_payload
        has_mfr_layout = payload is not None and len(payload) >= 6 and payload[0] in MODEL_CODES

        if not (name_match or has_mfr_layout):
            return None

        metadata: dict = {}
        if name:
            metadata["device_name"] = name
            # Bare 8-char serial likely IS the serial.
            if len(name) == 8 and name.isalnum():
                metadata["serial_number"] = name
            elif len(name) == 12 and all(c in "0123456789abcdefABCDEF" for c in name):
                metadata["serial_hex"] = name.lower()

        if has_mfr_layout:
            model_code = payload[0]
            metadata["model_code"] = model_code
            metadata["model"] = MODEL_CODES.get(model_code, f"Unknown_0x{model_code:02X}")
            metadata["protocol_version"] = payload[1]
            serial_hash = int.from_bytes(payload[3:5], "little")
            metadata["serial_hash"] = serial_hash
            metadata["mu_version_byte"] = payload[5]

        id_hash = hashlib.sha256(
            f"maytronics:{metadata.get('serial_number') or metadata.get('serial_hex') or raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="maytronics",
            beacon_type="maytronics",
            device_class="pool_cleaner",
            identifier_hash=id_hash,
            raw_payload_hex=(payload or b"").hex(),
            metadata=metadata,
        )
