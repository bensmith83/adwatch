"""Tempdrop BBT (basal body temperature) wearable plugin.

Per apk-ble-hunting/reports/tempdrop-tempdropmobileapp_passive.md.

The companion app does **zero** advertisement-payload parsing — no
``getManufacturerSpecificData`` / ``getServiceData`` call sites exist in the
whole decompiled tree. Discovery is:

  - local-name **prefix** ``"Tempdrop "`` (note the trailing space), and/or
  - service UUID ``0000F000-0000-1000-8000-00805F9B34FB``.

Only the name is registered as a match criterion. ``0xF000`` is the generic
Texas Instruments proprietary/OAD service base used by countless CC254x /
CC26xx designs, so matching it alone would mislabel unrelated TI devices as a
fertility wearable — a false positive with real privacy cost. The UUID is
instead used as *corroboration*, promoting confidence to ``high``.

All telemetry (temperature, acceleration, buffered-sample count, battery) is a
connected-GATT store-and-forward download; nothing sensor-related is broadcast.

Privacy: the static product-identifying name discloses the presence of a
fertility/BBT wearable to any passive observer, and reconnect uses a fixed MAC
(no RPA rotation in the app's model), so a band is trackable over time. Flagged
``sensitive=True`` so downstream collectors can scrub before logging.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


TEMPDROP_NAME_PREFIX = "Tempdrop "
TEMPDROP_NAME_PATTERN = r"^Tempdrop "
TEMPDROP_SERVICE_UUID = "f000"
_TEMPDROP_SERVICE_UUID_FULL = "0000f000-0000-1000-8000-00805f9b34fb"


@register_parser(
    name="tempdrop",
    local_name_pattern=TEMPDROP_NAME_PATTERN,
    description="Tempdrop BBT fertility wearable (presence-only)",
    version="1.0.0",
    core=False,
)
class TempdropParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        local_name = raw.local_name or ""
        if not local_name.startswith(TEMPDROP_NAME_PREFIX):
            return None

        normalized = [u.lower() for u in (raw.service_uuids or [])]
        uuid_seen = (
            TEMPDROP_SERVICE_UUID in normalized
            or _TEMPDROP_SERVICE_UUID_FULL in normalized
        )

        metadata: dict = {
            "vendor": "Tempdrop",
            "product": "Tempdrop BBT wearable",
            "device_name": local_name,
            "service_uuid_seen": uuid_seen,
            "confidence": "high" if uuid_seen else "medium",
            "telemetry": "none (connect-only GATT)",
            "sensitive": True,
            "sensitive_category": "reproductive_health",
        }

        # No stable in-payload identifier exists (nothing is broadcast), so the
        # MAC is the only per-unit anchor. The app reconnects by fixed MAC, so
        # it is expected to be stable.
        id_hash = hashlib.sha256(
            f"tempdrop:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="tempdrop",
            beacon_type="tempdrop",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
