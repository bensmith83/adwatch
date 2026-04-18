"""Ember Mug heated mug plugin.

Vendor service UUIDs per apk-ble-hunting/reports/embertech_passive.md.
Manufacturer-data model/color decoding is from the Home Assistant ember-mug
community integration — the Ember app itself does not parse ad mfr data
(telemetry is GATT-only).
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import _normalize_uuid, register_parser

EMBER_COMPANY_ID = 0x03C1

# Vendor service UUIDs identifying Ember mugs by generation.
EMBER_SERVICE_UUID_ORIGINAL = "fc543621-236c-4c94-8fa9-944a3e5353fa"
EMBER_SERVICE_UUID_CERAMIC = "fc543622-236c-4c94-8fa9-944a3e5353fa"
NORDIC_DFU_SERVICE_UUID = "00001530-1212-efde-1523-785feabcd123"

_GENERATION_BY_UUID = {
    _normalize_uuid(EMBER_SERVICE_UUID_ORIGINAL): "original",
    _normalize_uuid(EMBER_SERVICE_UUID_CERAMIC): "ceramic_mug",
}

MODEL_NAMES = {
    1: ("Mug", "10oz"),
    2: ("Mug", "14oz"),
    3: ("Travel Mug", None),
    8: ("Cup", "6oz"),
    9: ("Tumbler", "16oz"),
}

COLORS = {
    -131: "Copper", -127: "Black", -126: "White", -125: "Copper", -124: "Rose Gold",
    -123: "Stainless Steel", -120: "Red", -117: "Red", -63: "Black", -62: "White",
    -61: "Copper", -60: "Rose Gold", -59: "Stainless Steel", -57: "Blue",
    -56: "Red", -55: "Grey", -53: "Red", -52: "Sage Green", -51: "Sandstone",
    1: "Black", 2: "White", 3: "Copper", 8: "Red", 11: "Red", 14: "Black",
    51: "Copper", 65: "Black", 83: "Copper",
}


@register_parser(
    name="ember_mug",
    company_id=EMBER_COMPANY_ID,
    service_uuid=[EMBER_SERVICE_UUID_ORIGINAL, EMBER_SERVICE_UUID_CERAMIC],
    local_name_pattern=r"^Ember",
    description="Ember Mug heated drinkware",
    version="1.1.0",
    core=False,
)
class EmberMugParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        metadata: dict = {}

        uuid_generation = None
        dfu_mode = False
        for u in (raw.service_uuids or []):
            n = _normalize_uuid(u)
            if n in _GENERATION_BY_UUID:
                uuid_generation = _GENERATION_BY_UUID[n]
            if n == _normalize_uuid(NORDIC_DFU_SERVICE_UUID):
                dfu_mode = True
        if uuid_generation:
            metadata["service_generation"] = uuid_generation
        if dfu_mode:
            metadata["dfu_mode"] = True

        payload = raw.manufacturer_payload
        if not payload:
            if uuid_generation or dfu_mode:
                id_hash = hashlib.sha256(f"{raw.mac_address}:Ember".encode()).hexdigest()[:16]
                return ParseResult(
                    parser_name="ember_mug",
                    beacon_type="ember_mug",
                    device_class="drinkware",
                    identifier_hash=id_hash,
                    raw_payload_hex="",
                    metadata=metadata,
                )
            return None


        if len(payload) >= 4:
            # Extended format: header(1) + model_id(1) + generation(1) + color_id(1)
            model_id = payload[1]
            generation = payload[2]
            color_id = payload[3]
            metadata["model_id"] = model_id
            metadata["generation"] = generation
            metadata["color_id"] = color_id
            metadata["color"] = COLORS.get(color_id, "Unknown")
        else:
            # Short format: big-endian model int
            model_id = int.from_bytes(payload[:2], "big", signed=True) if len(payload) >= 2 else 0
            generation = 1
            metadata["model_id"] = model_id

        # Build model name
        base = MODEL_NAMES.get(model_id)
        if base:
            name_part, size = base
            if generation >= 2:
                if size:
                    model_name = f"{name_part} 2 ({size})"
                else:
                    model_name = f"{name_part} 2"
            else:
                if size:
                    model_name = f"{name_part} ({size})"
                else:
                    model_name = name_part
        else:
            model_name = f"Unknown ({model_id})"

        metadata["model_name"] = model_name

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:Ember".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="ember_mug",
            beacon_type="ember_mug",
            device_class="drinkware",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
