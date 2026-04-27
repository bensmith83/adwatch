"""Generic shape-based parser for service UUID 56D63956-93E7-11EE-B9D1-0242AC120002.

Vendor unidentified. Observed in a small bespoke supermarket on devices
believed to be refrigerated-shelf temperature sensors. The advertisement
itself only carries a stable 6-character ASCII sensor ID (likely a
back-end lookup key); telemetry probably flows over a separate channel
or only on connect.

The UUID is a UUIDv1 (timestamp 0x93E7-11EE = November 2023) with the
node field `0242AC120002` — Docker's bridge-network MAC OUI — strongly
suggesting it was generated programmatically inside a container by a
small in-house tooling shop.

Renaming candidates once the vendor is identified: keep the file name or
re-shape; the parser key `cold_chain_56d6` is stored in the database
and surfaces in the UI.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import _normalize_uuid, register_parser


COLD_CHAIN_56D6_UUID = "56d63956-93e7-11ee-b9d1-0242ac120002"
_COLD_CHAIN_UUID_NORMALIZED = _normalize_uuid(COLD_CHAIN_56D6_UUID)

# Observed payload shape: 0x00 + 6 ASCII chars (uppercase letters / digits).
_SENSOR_ID_RE = re.compile(rb"^[A-Z0-9]{6}$")


@register_parser(
    name="cold_chain_56d6",
    service_uuid=COLD_CHAIN_56D6_UUID,
    description="Cold-chain / refrigerated-shelf sensor (UUID 56D63956 — vendor TBD)",
    version="1.0.0",
    core=False,
)
class ColdChain56d6Parser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.service_data:
            return None

        body = None
        for key, value in raw.service_data.items():
            if _normalize_uuid(key) == _COLD_CHAIN_UUID_NORMALIZED:
                body = value
                break
        if body is None:
            return None

        # Strict shape: 7 bytes, leading 0x00, then 6 ASCII alphanumerics.
        if len(body) != 7 or body[0] != 0x00:
            return None
        sensor_id_bytes = body[1:]
        if not _SENSOR_ID_RE.match(sensor_id_bytes):
            return None
        sensor_id = sensor_id_bytes.decode("ascii")

        metadata: dict = {
            "sensor_id": sensor_id,
            "service_uuid": COLD_CHAIN_56D6_UUID,
        }
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        # sensor_id appears stable per-device; use it (not MAC) as the
        # identity basis so the sighting persists across MAC rotations.
        id_hash = hashlib.sha256(f"cold_chain_56d6:{sensor_id}".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="cold_chain_56d6",
            beacon_type="cold_chain_56d6",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=body.hex(),
            metadata=metadata,
        )
