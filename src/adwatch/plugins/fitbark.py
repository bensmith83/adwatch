"""FitBark pet activity collar plugin.

Per apk-ble-hunting/reports/fitbark-com-android_passive.md. FitBark
collars advertise three UUIDs across hardware generations:

  - **v1** (legacy collar): canonical 128-bit UUID
    ``46697442-6172-6b21-576f-6f66576f6f66`` — the bytes literally spell
    "FitBar!WooWoowoof". Also advertises the 16-bit alias ``0xFFA0``.
  - **v2 / GPS / v4**: ``46697442-6172-6b21-576f-6f66576f6f67`` (last
    byte changes from `f` to `g` — "FitBar!WooWoowoog").

Advertisement is presence-only — activity / GPS / battery is post-connect
GATT.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


FITBARK_V1_UUID = "46697442-6172-6b21-576f-6f66576f6f66"
FITBARK_V2_UUID = "46697442-6172-6b21-576f-6f66576f6f67"
FITBARK_LEGACY_UUID = "0000ffa0-0000-1000-8000-00805f9b34fb"


@register_parser(
    name="fitbark",
    service_uuid=[FITBARK_V1_UUID, FITBARK_V2_UUID, FITBARK_LEGACY_UUID],
    description="FitBark dog activity collar (v1 / v2 / GPS / v4)",
    version="1.0.0",
    core=False,
)
class FitbarkParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        v1_hit = FITBARK_V1_UUID in normalized
        v2_hit = FITBARK_V2_UUID in normalized
        legacy_hit = (
            FITBARK_LEGACY_UUID in normalized
            or "ffa0" in normalized
        )

        if not (v1_hit or v2_hit or legacy_hit):
            return None

        metadata: dict = {"vendor": "FitBark"}
        if v2_hit:
            metadata["generation"] = "v2_plus"
        else:
            # v1 UUID or the FFA0 legacy alias.
            metadata["generation"] = "v1"
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        id_basis = f"fitbark:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="fitbark",
            beacon_type="fitbark",
            device_class="pet_tracker",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
