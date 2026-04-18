"""Tapkey Mobile lock BLE advertisement parser.

Per apk-ble-hunting/reports/tpky-mc_passive.md. Service UUID
`6e65742e-7470-6b79-2ea0-000006060101` ("net.tpky." ASCII in bytes 0-7).
Manufacturer data: magic byte 1st position with bit 7 = isLockIdIncomplete;
bytes 1+ = incomplete lock ID.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


TAPKEY_SERVICE_UUID = "6e65742e-7470-6b79-2ea0-000006060101"


@register_parser(
    name="tapkey",
    service_uuid=TAPKEY_SERVICE_UUID,
    description="Tapkey Mobile electronic locks",
    version="1.0.0",
    core=False,
)
class TapkeyParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        has_uuid = TAPKEY_SERVICE_UUID in [u.lower() for u in (raw.service_uuids or [])]

        magic_match = False
        lock_id_fragment = None
        is_incomplete = None

        payload = raw.manufacturer_payload
        if payload and len(payload) >= 1:
            magic = payload[0]
            if (magic & 0x7F) == 1:
                magic_match = True
                is_incomplete = bool(magic & 0x80)
                lock_id_fragment = payload[1:].hex() if len(payload) > 1 else ""

        if not (has_uuid or magic_match):
            return None

        metadata: dict = {}
        if has_uuid:
            metadata["has_tapkey_service"] = True
        if magic_match:
            metadata["magic_match"] = True
            metadata["is_lock_id_incomplete"] = is_incomplete
            if lock_id_fragment:
                metadata["lock_id_fragment_hex"] = lock_id_fragment
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        if lock_id_fragment:
            id_basis = f"tapkey:{lock_id_fragment}"
        else:
            id_basis = f"tapkey:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="tapkey",
            beacon_type="tapkey",
            device_class="lock",
            identifier_hash=id_hash,
            raw_payload_hex=(payload or b"").hex(),
            metadata=metadata,
        )
