"""Dyson connected-product plugin.

Per apk-ble-hunting/reports/dyson-mobile-android_passive.md:

  - Pre-provisioning (factory state): advertises service UUID
    2DD10010-1C37-452D-8979-D1B4A787D0A4 (Dyson Auth/LEC service).
  - Post-provisioning: emits a "machine-found" beacon under company ID
    0x0A12 (Dyson Limited) with the constant 2-byte prefix 0x01 0x01.

  Bytes 4+ of the post-provisioning beacon are not specified in the app's
  scan filter — likely carry per-machine state. Exposed as raw hex for
  future field-trace analysis.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


DYSON_COMPANY_ID = 0x0A12  # 2578
DYSON_AUTH_SERVICE_UUID = "2dd10010-1c37-452d-8979-d1b4a787d0a4"
DYSON_BEACON_PREFIX = b"\x01\x01"


@register_parser(
    name="dyson",
    company_id=DYSON_COMPANY_ID,
    service_uuid=DYSON_AUTH_SERVICE_UUID,
    local_name_pattern=r"^Dyson ",
    description="Dyson connected vacuums / purifiers / hair-care",
    version="1.0.0",
    core=False,
)
class DysonParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        uuid_hit = DYSON_AUTH_SERVICE_UUID in normalized
        cid_hit = raw.company_id == DYSON_COMPANY_ID
        name_hit = bool(raw.local_name and raw.local_name.startswith("Dyson "))

        if not (uuid_hit or cid_hit or name_hit):
            return None

        metadata: dict = {}

        if uuid_hit:
            metadata["state"] = "unprovisioned"
            metadata["auth_service_advertised"] = True

        payload = raw.manufacturer_payload
        if cid_hit and payload:
            if payload.startswith(DYSON_BEACON_PREFIX):
                metadata["state"] = "provisioned_beacon"
                metadata["beacon_prefix_match"] = True
                if len(payload) > 2:
                    metadata["state_bytes_hex"] = payload[2:].hex()
            else:
                metadata["beacon_prefix_match"] = False

        if raw.local_name and raw.local_name.startswith("Dyson "):
            metadata["device_name"] = raw.local_name
            metadata["model_hint"] = raw.local_name[len("Dyson "):]

        id_hash = hashlib.sha256(f"dyson:{raw.mac_address}".encode()).hexdigest()[:16]
        raw_hex = payload.hex() if payload else ""

        return ParseResult(
            parser_name="dyson",
            beacon_type="dyson",
            device_class="appliance",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )

    def storage_schema(self):
        return None
