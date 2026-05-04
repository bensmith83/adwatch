"""Meross plugin (v1 legacy + v2 MS605 presence sensor).

Per apk-ble-hunting/reports/meross-meross_passive.md. Two non-Matter
families distinguished:

  - **v1 legacy** (MSS plugs / MSL bulbs pre-Matter): service UUID
    ``0x0000A00A`` + name prefix ``RFBL_`` or ``MRBL_`` followed by
    a 12-char hex BD_ADDR (uppercase).
  - **v2 MS605 presence sensor**: manufacturer-data under the SIG
    "test/reserved" CID ``0xFFFF`` carrying a TLV frame; subdev-type
    ``0xC0`` identifies the MS605.

The third Meross path (Matter MSMC series via ``0xFFF6``) is handled by
``plugins/matter.py`` and intentionally not duplicated here.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


MEROSS_V1_UUID = "0000a00a-0000-1000-8000-00805f9b34fb"
MEROSS_V2_CID = 0xFFFF  # SIG "test/reserved" — Meross ships in production

_SUBDEV_TYPES = {
    0xC0: "ms605",
}

_NAME_RE = re.compile(r"^(RFBL_|MRBL_)([0-9A-Fa-f]{12})$")


@register_parser(
    name="meross",
    company_id=MEROSS_V2_CID,
    service_uuid=MEROSS_V1_UUID,
    local_name_pattern=r"^(RFBL_|MRBL_)",
    description="Meross v1 legacy + v2 MS605 (non-Matter paths)",
    version="1.0.0",
    core=False,
)
class MerossParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        v1_uuid_hit = MEROSS_V1_UUID in normalized
        v2_cid_hit = raw.company_id == MEROSS_V2_CID

        local_name = raw.local_name or ""
        name_match = _NAME_RE.match(local_name)

        if not (v1_uuid_hit or v2_cid_hit or name_match):
            return None

        # v2 MS605 must satisfy more than just the SIG "test" CID — match the
        # TLV shape (type / length / subdev) before claiming the sighting.
        v2_decoded = False
        metadata: dict = {"vendor": "Meross"}

        if v1_uuid_hit or name_match:
            metadata["product_family"] = "meross_v1"
            if name_match:
                metadata["device_name"] = local_name
                hex_mac = name_match.group(2).upper()
                mac_str = ":".join(hex_mac[i:i+2] for i in range(0, 12, 2))
                metadata["mac_in_name"] = mac_str
        elif v2_cid_hit:
            payload = raw.manufacturer_payload or b""
            if len(payload) >= 3:
                # Skip TLV type+length and read subdev-type byte.
                subdev = payload[2]
                metadata["product_family"] = "meross_v2"
                metadata["subdev_type"] = _SUBDEV_TYPES.get(subdev, f"unknown_0x{subdev:02X}")
                metadata["tlv_type"] = payload[0]
                metadata["tlv_length"] = payload[1]
                v2_decoded = True
            else:
                # CID 0xFFFF without a recognizable TLV is not necessarily
                # Meross — bail to avoid false positives.
                return None

        # If the only signal is the v2 CID and it didn't decode cleanly,
        # we already returned None above.

        if metadata.get("mac_in_name"):
            id_basis = f"meross:{metadata['mac_in_name']}"
        else:
            id_basis = f"meross:{metadata.get('product_family', 'unknown')}:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="meross",
            beacon_type="meross",
            device_class="smart_home",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
