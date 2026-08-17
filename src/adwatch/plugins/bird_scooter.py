"""Bird shared e-scooter advertisement parser.

Per apk-ble-hunting/reports/bird-android_passive.md.

Bird scooters advertise the vendor-squatted SIG-base 16-bit service UUID
``0xB13D`` ("BIRD" in leetspeak) — the rider app's only deterministic scan
filter (``GattUuid.java:69``). The advertised local name is the other
persistent handle; public reverse-engineering puts it in the shape
``Bird-XXXX`` (or a bare IMEI tail).

The manufacturer-data byte layout is **not** decodable from the APK: the
rider app forwards the whole scan envelope (rssi, name, serviceIds,
manufacturerData, MAC) to Bird's cloud, which owns the format and returns the
matching ``Vehicle.imei``. We therefore surface the raw bytes verbatim rather
than inventing a layout — a live capture is needed to decode them.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import _normalize_uuid, register_parser


BIRD_SERVICE_UUID = "b13d"
_BIRD_UUID_NORMALIZED = _normalize_uuid(BIRD_SERVICE_UUID)

# `Bird-1A2B` / `Bird 1A2B` / `BIRD-123456789012345` (IMEI tail).
BIRD_NAME_PATTERN = r"^(?i:bird)[-_ ]([0-9A-Za-z]{4,15})$"
_BIRD_NAME_RE = re.compile(BIRD_NAME_PATTERN)


@register_parser(
    name="bird_scooter",
    service_uuid=BIRD_SERVICE_UUID,
    local_name_pattern=BIRD_NAME_PATTERN,
    description="Bird shared e-scooters (0xB13D service UUID)",
    version="1.0.0",
    core=False,
)
class BirdScooterParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        has_uuid = any(
            _normalize_uuid(u) == _BIRD_UUID_NORMALIZED
            for u in (raw.service_uuids or [])
        )
        name = raw.local_name or ""
        name_match = _BIRD_NAME_RE.match(name)

        if not (has_uuid or name_match):
            return None

        metadata: dict = {"vendor": "Bird"}
        if has_uuid:
            metadata["has_bird_service_uuid"] = True
            metadata["service_uuid"] = BIRD_SERVICE_UUID
        if name:
            metadata["device_name"] = name
        if name_match:
            metadata["unit_id"] = name_match.group(1)

        payload = raw.manufacturer_payload
        if payload:
            # Layout is resolved server-side; log, do not guess.
            metadata["manufacturer_payload_hex"] = payload.hex()
            metadata["payload_decode"] = "server_side_only"
        if raw.manufacturer_data:
            metadata["company_id_hex"] = f"0x{raw.company_id:04X}"

        if name_match:
            id_basis = f"bird:{name}"
        else:
            id_basis = f"bird:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="bird_scooter",
            beacon_type="bird_scooter",
            device_class="vehicle",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
