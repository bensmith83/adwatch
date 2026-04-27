"""Tuya / Smart Life BLE advertisement plugin."""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

TUYA_COMPANY_ID = 0x07D0

# Cheap Tuya-clone WiFi smart devices (plugs, bulbs) advertise this exact
# name shape in pairing mode. They typically don't carry the SIG-correct
# Tuya CID — name is the only signal. Locked to uppercase/digit pairs to
# stay narrow.
_TUYA_CLONE_NAME_RE = re.compile(r"^Smart\.[A-Z0-9]{2}\.WIFI$")


@register_parser(
    name="tuya",
    company_id=TUYA_COMPANY_ID,
    local_name_pattern=_TUYA_CLONE_NAME_RE.pattern,
    description="Tuya / Smart Life BLE advertisements (incl. cheap-clone pairing-mode name)",
    version="1.1.0",
    core=False,
)
class TuyaParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        local_name = getattr(raw, "local_name", None) or ""

        # CID path — full Tuya BLE protocol decode.
        if raw.manufacturer_data and len(raw.manufacturer_data) >= 4:
            company_id = int.from_bytes(raw.manufacturer_data[:2], "little")
            if company_id == TUYA_COMPANY_ID:
                payload = raw.manufacturer_data[2:]
                if len(payload) < 2:
                    return None

                protocol_version = payload[0]
                flags = payload[1]
                pairing = bool(flags & 0x01)

                metadata: dict = {
                    "protocol_version": protocol_version,
                    "flags": flags,
                    "pairing": pairing,
                }

                if len(payload) > 2:
                    metadata["product_id_hex"] = payload[2:].hex()

                if local_name:
                    metadata["local_name"] = local_name

                id_hash = hashlib.sha256(
                    f"{raw.mac_address}:tuya".encode()
                ).hexdigest()[:16]

                return ParseResult(
                    parser_name="tuya",
                    beacon_type="tuya",
                    device_class="smart_home",
                    identifier_hash=id_hash,
                    raw_payload_hex=payload.hex(),
                    metadata=metadata,
                )

        # Cheap-clone name-only path — pairing-mode `Smart.<XX>.WIFI`.
        if _TUYA_CLONE_NAME_RE.match(local_name):
            id_hash = hashlib.sha256(
                f"{raw.mac_address}:tuya".encode()
            ).hexdigest()[:16]
            return ParseResult(
                parser_name="tuya",
                beacon_type="tuya",
                device_class="smart_home",
                identifier_hash=id_hash,
                raw_payload_hex="",
                metadata={
                    "local_name": local_name,
                    "match_source": "name_regex",
                    "pairing_mode_clone": True,
                    "pairing": True,
                },
            )

        return None

    def storage_schema(self):
        return None
