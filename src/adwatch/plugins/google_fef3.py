"""Google FEF3 cross-device companion beacon parser.

0xFEF3 is a BT-SIG-assigned service UUID owned by Google LLC. The frame
is a 27-byte rotating opaque identifier — a lower-volume sibling of the
FCF1 and FE9F surfaces. Presence-only parser.
"""

import hashlib

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import register_parser

FEF3_UUID = "fef3"


@register_parser(
    name="google_fef3",
    service_uuid=FEF3_UUID,
    description="Google FEF3 companion beacon",
    version="1.0.0",
    core=False,
)
class GoogleFef3Parser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.service_data:
            return None
        payload = raw.service_data.get(FEF3_UUID)
        if not payload:
            return None

        metadata: dict = {
            "payload_length": len(payload),
            "payload_hex": payload.hex(),
        }

        id_hash = hashlib.sha256(
            f"google_fef3:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="google_fef3",
            beacon_type="google_fef3",
            device_class="phone",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata=metadata,
        )
