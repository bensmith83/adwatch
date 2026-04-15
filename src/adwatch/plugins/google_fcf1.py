"""Google FCF1 cross-device beacon parser.

0xFCF1 is a BT-SIG-assigned service UUID owned by Google LLC. Recent
Pixel/Play-services builds broadcast a 22-byte rotating frame on this
UUID as part of an undocumented Cross-Device proximity surface. The
frame is opaque to non-account observers; we capture the frame type and
rotating payload for presence detection.
"""

import hashlib

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import register_parser

FCF1_UUID = "fcf1"


@register_parser(
    name="google_fcf1",
    service_uuid=FCF1_UUID,
    description="Google Cross-Device FCF1 beacon",
    version="1.0.0",
    core=False,
)
class GoogleFcf1Parser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.service_data:
            return None
        payload = raw.service_data.get(FCF1_UUID)
        if not payload:
            return None

        metadata: dict = {
            "frame_type": payload[0],
            "payload_length": len(payload),
            "payload_hex": payload.hex(),
        }

        id_hash = hashlib.sha256(
            f"google_fcf1:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="google_fcf1",
            beacon_type="google_fcf1",
            device_class="phone",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata=metadata,
        )
