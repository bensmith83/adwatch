"""Barking Labs Fi dog collar BLE advertisement parser.

Per apk-ble-hunting/reports/barkinglabs-fi_passive.md. Service-UUID detection
only — no mfr/service data telemetry.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import _normalize_uuid, register_parser


COLLAR_UUID = "57b40001-2528-d6bc-b043-b49af0ec06c1"
BASE_CONFIG_UUID = "57b40210-2528-d6bc-b043-b49af0ec06c1"
BASE_PROXY_UUID = "57b43001-2528-d6bc-b043-b49af0ec06c1"

_ROLE_BY_UUID = {
    _normalize_uuid(COLLAR_UUID): "collar",
    _normalize_uuid(BASE_CONFIG_UUID): "base_config",
    _normalize_uuid(BASE_PROXY_UUID): "base_proxy",
}


@register_parser(
    name="barkinglabs_fi",
    service_uuid=[COLLAR_UUID, BASE_CONFIG_UUID, BASE_PROXY_UUID],
    description="Barking Labs Fi smart dog collar",
    version="1.0.0",
    core=False,
)
class BarkingLabsFiParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        role = None
        for u in (raw.service_uuids or []):
            r = _ROLE_BY_UUID.get(_normalize_uuid(u))
            if r:
                role = r
                break

        if role is None:
            return None

        metadata: dict = {"role": role}
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        id_hash = hashlib.sha256(f"fi:{raw.mac_address}".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="barkinglabs_fi",
            beacon_type="barkinglabs_fi",
            device_class="pet_tracker",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )
