"""Sony Audio BLE advertisement parser."""

import hashlib
import re

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import register_parser

SONY_COMPANY_ID = 0x012D
SONY_NAME_RE = re.compile(r"^LE_(SRS|WF|WH|WI)-")

DEVICE_CLASS_MAP = {
    "SRS": "speaker",
    "WH": "headphones",
    "WF": "earbuds",
    "WI": "headphones",
}


@register_parser(
    name="sony_audio",
    company_id=SONY_COMPANY_ID,
    local_name_pattern=r"^LE_(SRS|WF|WH|WI)-",
    description="Sony Audio devices (speakers, headphones, earbuds)",
    version="1.0.0",
    core=False,
)
class SonyAudioParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        has_mfr = raw.manufacturer_data and len(raw.manufacturer_data) >= 2 and raw.company_id == SONY_COMPANY_ID

        # Check fe2c service data — only Sony frames (0x00, 0x30), reject 0x40+ (FMDN)
        fe2c_data = None
        if raw.service_data and "fe2c" in raw.service_data:
            data = raw.service_data["fe2c"]
            if data and len(data) >= 2 and data[0] < 0x40:
                fe2c_data = data

        if not has_mfr and not fe2c_data:
            return None

        metadata: dict = {}

        # Parse manufacturer data
        if has_mfr and len(raw.manufacturer_data) >= 4:
            payload = raw.manufacturer_data[2:]
            metadata["version"] = payload[0]
            metadata["device_type"] = payload[1]
            metadata["model_id"] = payload[2] if len(payload) > 2 else None

        # Parse fe2c service data
        if fe2c_data and len(fe2c_data) >= 2:
            # byte[0] is header (always 0x00 for Sony), byte[1] encodes frame type
            # Values < 0x40 are frame types (0x00, 0x30); >= 0x80 are sub-types within type 0x00
            frame_byte = fe2c_data[1]
            metadata["frame_type"] = frame_byte if frame_byte < 0x40 else 0x00
            metadata["sub_type"] = frame_byte

        # Device classification from local name
        device_class = "audio"
        if raw.local_name:
            m = SONY_NAME_RE.match(raw.local_name)
            if m:
                device_class = DEVICE_CLASS_MAP.get(m.group(1), "audio")
                metadata["model"] = raw.local_name[3:]  # Strip "LE_"

        id_hash = hashlib.sha256(
            f"sony_audio:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        raw_hex = raw.manufacturer_data.hex() if has_mfr else (fe2c_data.hex() if fe2c_data else "")

        return ParseResult(
            parser_name="sony_audio",
            beacon_type="sony_audio",
            device_class=device_class,
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )
