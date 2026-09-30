"""Oura Ring plugin.

Identification per apk-ble-hunting/reports/ouraring-oura_passive.md:

  - Service UUID 98ED0001-A541-11E4-B6A0-0002A5D5C51B (ring data),
    8BC5888F-C577-4F5D-857F-377354093F13 (charger puck).
  - Manufacturer data under company_id 0x02B2 (Oura Health Oy, per the
    Bluetooth SIG Assigned Numbers company_identifiers.yaml).

Mfr-data layout (post-CID strip), from name-matched NearSight corpus
captures (2026-09-29)::

    payload[0]    frame type (0x04 observed on every ring frame)
    payload[1]    generation byte: 0x40 Gen 3, 0x60 Ring 4, 0x70 Ring 5
    payload[2:4]  firmware / protocol revision, LE uint16

v1.1 corrections:

* v1.0 split payload[1] into hwtype (high nibble) / mode (low nibble)
  using enum tables from the decompiled app, and payload[2..3] into
  colour/battery/design nibbles.  The corpus contradicts that: the
  name-matched Gen3 / Ring 4 / Ring 5 frames carry payload[1] = 0x40 /
  0x60 / 0x70 (so Gen3 decoded as "BENTLEY" and Ring 4/5 as unknown, all in
  mode "UNKNOWN"), and payload[2..3] behaves as a small LE counter
  (0x0118-0x015C with a constant 0x01 high byte on Ring 4).  Those nibble
  decodes are removed.
* The app also scan-filters on 00060000-F8CE-11E4-ABF4-0002A5D5C51B, but
  that is Cypress's generic bootloader (OTA/DFU) service, used by any
  product on a Cypress PSoC/CYW part, so it no longer routes here.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


OURA_COMPANY_ID = 0x02B2

OURA_DATA_SERVICE_UUID = "98ed0001-a541-11e4-b6a0-0002a5d5c51b"
OURA_CHARGER_SERVICE_UUID = "8bc5888f-c577-4f5d-857f-377354093f13"
# Cypress generic bootloader service — NOT routed (see module docstring).
CYPRESS_BOOTLOADER_SERVICE_UUID = "00060000-f8ce-11e4-abf4-0002a5d5c51b"

FRAME_TYPE_RING = 0x04

# Generation byte (payload[1]) from name-matched corpus captures.
GENERATIONS = {
    0x40: "Gen 3",
    0x60: "Ring 4",
    0x70: "Ring 5",
}


@register_parser(
    name="oura",
    company_id=OURA_COMPANY_ID,
    service_uuid=(OURA_DATA_SERVICE_UUID, OURA_CHARGER_SERVICE_UUID),
    description="Oura Ring (Gen 3 / Ring 4 / Ring 5) and charger puck",
    version="1.1.0",
    core=False,
)
class OuraParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        cid_hit = raw.company_id == OURA_COMPANY_ID
        data_hit = OURA_DATA_SERVICE_UUID in normalized
        charger_hit = OURA_CHARGER_SERVICE_UUID in normalized

        if not (cid_hit or data_hit or charger_hit):
            return None

        metadata: dict = {}

        if charger_hit:
            metadata["device_kind"] = "charger_puck"
        else:
            metadata["device_kind"] = "ring"

        payload = raw.manufacturer_payload
        if cid_hit and payload and len(payload) >= 2:
            metadata["frame_type"] = payload[0]
            gen_byte = payload[1]
            metadata["generation_byte"] = gen_byte
            if gen_byte in GENERATIONS:
                metadata["generation"] = GENERATIONS[gen_byte]
            if len(payload) >= 4:
                metadata["fw_revision"] = int.from_bytes(payload[2:4], "little")

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
