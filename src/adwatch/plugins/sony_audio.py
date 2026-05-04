"""Sony Audio BLE advertisement parser.

Enriched per apk-ble-hunting/reports/sony-songpal-mdr_passive.md:

  - Sony company_id `0x012D` (301).
  - Family tag at payload[2..3]:
      `04 00` = SONY_AUDIO (headphones / earbuds)
      `0A 00` = SONY_LIGHTING (SRS speakers)
  - Subtype byte at payload[4]: 0x01 = primary advert, 0x02 = scan-response.
  - Pseudo-iBeacon variant under Apple CID `0x004C` with fixed proximity
    UUID `00000000-7A46-1001-B000-001C4D2CA2D7` (Sony's iBeacon prefix).
  - Some products also expose Fast Pair (FE2C) service data.
"""

import hashlib
import re

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import register_parser

SONY_COMPANY_ID = 0x012D
APPLE_COMPANY_ID = 0x004C

# Family tags at payload[2..3] (little-endian uint16).
FAMILY_AUDIO = 0x0004
FAMILY_LIGHTING = 0x000A

FAMILY_NAMES = {FAMILY_AUDIO: "audio", FAMILY_LIGHTING: "lighting"}

# Sony pseudo-iBeacon proximity UUID prefix (first 16 bytes inside Apple mfr-data).
SONY_IBEACON_PREFIX = bytes.fromhex("000000007a461001b000001c4d2ca2d7")

SONY_NAME_RE = re.compile(r"^LE_(SRS|WF|WH|WI)-")

DEVICE_CLASS_MAP = {
    "SRS": "speaker",
    "WH": "headphones",
    "WF": "earbuds",
    "WI": "headphones",
}


def _detect_sony_ibeacon(payload: bytes) -> bool:
    """Apple iBeacon framing where the proximity UUID matches Sony's prefix."""
    if not payload or len(payload) < 22:
        return False
    if payload[0] != 0x02 or payload[1] != 0x15:
        return False
    return payload[2:18] == SONY_IBEACON_PREFIX


@register_parser(
    name="sony_audio",
    company_id=(SONY_COMPANY_ID, APPLE_COMPANY_ID),
    local_name_pattern=r"^LE_(SRS|WF|WH|WI)-",
    description="Sony Audio devices (speakers, headphones, earbuds)",
    version="2.0.0",
    core=False,
)
class SonyAudioParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        cid = raw.company_id
        payload = raw.manufacturer_payload

        # Detect Sony pseudo-iBeacon (Apple CID + Sony proximity UUID prefix).
        sony_ibeacon = (
            cid == APPLE_COMPANY_ID and payload is not None
            and _detect_sony_ibeacon(payload)
        )

        # Standard Sony mfr-data path — CID match alone is enough to identify.
        sony_audio_or_lighting_mfr = cid == SONY_COMPANY_ID

        # Fast Pair (Sony — frame 0x00 family).
        fe2c_data = None
        if raw.service_data and "fe2c" in raw.service_data:
            data = raw.service_data["fe2c"]
            if data and len(data) >= 2 and data[0] < 0x40:
                fe2c_data = data

        if not (sony_ibeacon or sony_audio_or_lighting_mfr or fe2c_data):
            return None

        metadata: dict = {}

        # Sony pseudo-iBeacon path.
        if sony_ibeacon:
            metadata["frame_type"] = "sony_ibeacon"
            metadata["sony_proximity_uuid"] = (
                "00000000-7a46-1001-b000-001c4d2ca2d7"
            )
            if len(payload) >= 24:
                metadata["ibeacon_major"] = (payload[18] << 8) | payload[19]
                metadata["ibeacon_minor"] = (payload[20] << 8) | payload[21]

        # SONY_AUDIO / SONY_LIGHTING family tag decode.
        if sony_audio_or_lighting_mfr and payload and len(payload) >= 2:
            family_tag = payload[0] | (payload[1] << 8)
            metadata["family_tag"] = family_tag
            metadata["family"] = FAMILY_NAMES.get(family_tag, f"unknown_{family_tag:04x}")
            if len(payload) >= 3:
                metadata["subtype"] = payload[2]
            # Legacy fields preserved for backward-compat with existing tests.
            metadata["version"] = payload[0]
            metadata["device_type"] = payload[1]
            metadata["model_id"] = payload[2] if len(payload) > 2 else None

        # Fast Pair / FE2C decode.
        if fe2c_data and len(fe2c_data) >= 2:
            frame_byte = fe2c_data[1]
            metadata["frame_type"] = frame_byte if frame_byte < 0x40 else 0x00
            metadata["sub_type"] = frame_byte

        # Device classification from local name.
        device_class = "audio"
        if raw.local_name:
            m = SONY_NAME_RE.match(raw.local_name)
            if m:
                device_class = DEVICE_CLASS_MAP.get(m.group(1), "audio")
                metadata["model"] = raw.local_name[3:]

        # Identity hash: Sony iBeacon major/minor is a stable per-device pair
        # (across MAC rotation) when present.
        if sony_ibeacon and "ibeacon_major" in metadata:
            id_basis = (
                f"sony_audio:ib:"
                f"{metadata['ibeacon_major']:04x}:{metadata['ibeacon_minor']:04x}"
            )
        else:
            id_basis = f"sony_audio:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        raw_hex = (
            raw.manufacturer_data.hex() if raw.manufacturer_data
            else (fe2c_data.hex() if fe2c_data else "")
        )

        return ParseResult(
            parser_name="sony_audio",
            beacon_type="sony_audio",
            device_class=device_class,
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )

    def storage_schema(self):
        return None
