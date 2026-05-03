"""Tacx smart trainer plugin (Neo / Flux / Vortex / Bushido / Genius / Smart Bike).

Per apk-ble-hunting/reports/tacx-android_passive.md. Three vendor service-UUID
families distinguish product generation:

  - **Neo / Flux**: ``8EC90001-F315-4F60-9FB8-838830DAEA50``
  - **Smart Bike**: ``FE03A000-…`` and ``FE031000-…``
  - **Legacy** (Vortex / Bushido / Genius): ``669A**05-0C08-969E-E211-86AD5062675F``
    where ``**`` ∈ {A2, A3, A4, A5, A6} encodes the model family.

Generic SIG profile UUIDs (FTMS `0x1826`, CPS `0x1818`, Garmin `0xFE1F`) are
NOT matched here because they're vendor-agnostic and would steal sightings
from non-Tacx trainers / power meters.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


TACX_NEO_FLUX_UUID = "8ec90001-f315-4f60-9fb8-838830daea50"

TACX_SMART_BIKE_UUIDS = [
    "fe03a000-17d0-470a-8798-4ad3e1c1f35b",
    "fe031000-17d0-470a-8798-4ad3e1c1f35b",
]

TACX_LEGACY_UUIDS = [
    "669aa205-0c08-969e-e211-86ad5062675f",
    "669aa305-0c08-969e-e211-86ad5062675f",
    "669aa405-0c08-969e-e211-86ad5062675f",
    "669aa505-0c08-969e-e211-86ad5062675f",
    "669aa605-0c08-969e-e211-86ad5062675f",
]

_ALL_UUIDS = [TACX_NEO_FLUX_UUID] + TACX_SMART_BIKE_UUIDS + TACX_LEGACY_UUIDS


@register_parser(
    name="tacx",
    service_uuid=_ALL_UUIDS,
    local_name_pattern=r"^TACX ",
    description="Tacx smart trainers (Neo/Flux/Smart Bike/legacy Vortex/Bushido/Genius)",
    version="1.0.0",
    core=False,
)
class TacxParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]

        family: str | None = None
        if TACX_NEO_FLUX_UUID in normalized:
            family = "neo_flux"
        elif any(u in normalized for u in TACX_SMART_BIKE_UUIDS):
            family = "smart_bike"
        elif any(u in normalized for u in TACX_LEGACY_UUIDS):
            family = "legacy"

        local_name = raw.local_name or ""
        name_hit = local_name.startswith("TACX ")

        if not (family or name_hit):
            return None

        metadata: dict = {"vendor": "Tacx"}
        if family:
            metadata["product_family"] = family
        if local_name:
            metadata["device_name"] = local_name

        id_basis = f"tacx:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="tacx",
            beacon_type="tacx",
            device_class="smart_trainer",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
