"""Oura Ring plugin.

Per apk-ble-hunting/reports/ouraring-oura_passive.md:

  - Service UUID 98ED0001-A541-11E4-B6A0-0002A5D5C51B (ring data),
    8BC5888F-C577-4F5D-857F-377354093F13 (charger puck),
    00060000-f8ce-11e4-abf4-0002a5d5c51b (Cypress DFU bootloader).
  - Manufacturer data under company_id 0x02B2 (Oura Health Ltd, 690).

Mfr-data layout (post-CID strip):
  payload[0] — hwtype/mode packed (byte0 of "b" in source)
  payload[1] — low 4 bits = mode, high 4 bits = hwtype key
  payload[2] — low 4 bits = i (battery/charge nibble), high 4 bits = color index
  payload[3] — low 4 bits = design code
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


OURA_COMPANY_ID = 0x02B2

OURA_DATA_SERVICE_UUID = "98ed0001-a541-11e4-b6a0-0002a5d5c51b"
OURA_CHARGER_SERVICE_UUID = "8bc5888f-c577-4f5d-857f-377354093f13"
OURA_DFU_SERVICE_UUID = "00060000-f8ce-11e4-abf4-0002a5d5c51b"

HARDWARE_TYPES = {
    0x00: "UNKNOWN",
    0x01: "GEN3",
    0x02: "GEN4",
    0x03: "COOPER",
    0x04: "BENTLEY",
}

RING_MODES = {
    0x00: "UNKNOWN",
    0x01: "OPERATING",
    0x02: "FIRMWARE",
    0x03: "BOOTLOADER",
}


@register_parser(
    name="oura",
    company_id=OURA_COMPANY_ID,
    service_uuid=(OURA_DATA_SERVICE_UUID, OURA_CHARGER_SERVICE_UUID, OURA_DFU_SERVICE_UUID),
    description="Oura Ring (Gen3/Gen4/Cooper/Bentley) and charger puck",
    version="1.0.0",
    core=False,
)
class OuraParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        cid_hit = raw.company_id == OURA_COMPANY_ID
        data_hit = OURA_DATA_SERVICE_UUID in normalized
        charger_hit = OURA_CHARGER_SERVICE_UUID in normalized
        dfu_hit = OURA_DFU_SERVICE_UUID in normalized

        if not (cid_hit or data_hit or charger_hit or dfu_hit):
            return None

        metadata: dict = {}

        if charger_hit:
            metadata["device_kind"] = "charger_puck"
        elif dfu_hit:
            metadata["device_kind"] = "ring"
            metadata["mode"] = "BOOTLOADER"
        else:
            metadata["device_kind"] = "ring"

        payload = raw.manufacturer_payload
        if cid_hit and payload and len(payload) >= 2:
            mode_nibble = payload[1] & 0x0F
            hwtype_nibble = (payload[1] >> 4) & 0x0F
            metadata["mode_code"] = mode_nibble
            metadata["mode"] = RING_MODES.get(mode_nibble, f"UNKNOWN_{mode_nibble}")
            metadata["hardware_type_code"] = hwtype_nibble
            metadata["hardware_type"] = HARDWARE_TYPES.get(
                hwtype_nibble, f"UNKNOWN_{hwtype_nibble}"
            )

            if len(payload) >= 3:
                i_nibble = payload[2] & 0x0F
                color_nibble = (payload[2] >> 4) & 0x0F
                metadata["i_nibble"] = i_nibble  # battery/charge — semantics TBD
                metadata["color_code"] = color_nibble

            if len(payload) >= 4:
                metadata["design_code"] = payload[3] & 0x0F

        if raw.local_name:
            metadata["device_name"] = raw.local_name

        id_hash = hashlib.sha256(f"oura:{raw.mac_address}".encode()).hexdigest()[:16]
        raw_hex = payload.hex() if payload else ""

        return ParseResult(
            parser_name="oura",
            beacon_type="oura",
            device_class="wearable",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )

    def storage_schema(self):
        return None
