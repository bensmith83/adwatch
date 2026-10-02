"""moonbird handheld guided-breathing device plugin.

Per apk-ble-hunting/reports/moonbird-app_passive.md.

The app (react-native-ble-plx, mfr data includes the CID) matches the hex
prefix ``6309`` = CID 0x0963 (LE) and reads full-mfr bytes 2-7 as a 6-char
ASCII serial -> ``manufacturer_payload[0:6]``. No telemetry is advertised.

Identity = ASCII serial (persistent, cross-platform); MAC fallback.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


MOONBIRD_COMPANY_ID = 0x0963


@register_parser(
    name="moonbird",
    company_id=MOONBIRD_COMPANY_ID,
    description="moonbird breathing biofeedback device (CID 0x0963 + ASCII serial)",
    version="1.0.0",
    core=False,
)
class MoonbirdParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if raw.company_id != MOONBIRD_COMPANY_ID:
            return None
        payload = raw.manufacturer_payload or b""
        metadata: dict = {"vendor": "moonbird", "product": "moonbird",
                          "telemetry": "none (GATT only)"}
        identity = f"moonbird:{raw.mac_address}"

        if len(payload) >= 6:
            serial_bytes = payload[0:6]
            metadata["serial_hex"] = serial_bytes.hex()
            if all(0x20 <= b < 0x7F for b in serial_bytes):
                serial = serial_bytes.decode("ascii")
                metadata["serial_number"] = serial
                identity = f"moonbird:{serial}"
            if len(payload) > 6:
                metadata["trailing_hex"] = payload[6:].hex()

        return ParseResult(
            parser_name="moonbird",
            beacon_type="moonbird",
            device_class="wearable",
            identifier_hash=hashlib.sha256(identity.encode()).hexdigest()[:16],
            raw_payload_hex=payload.hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
