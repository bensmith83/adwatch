"""Polar fitness device BLE advertisement parser.

HR straps, watches, optical armbands, and scales. Per
apk-ble-hunting/reports/polar-polarflow_passive.md. Key finding: bonded Polar
devices broadcast the Polar Flow account user-ID in cleartext in every
advertisement (`PbMasterIdentifierBroadcast`), enabling per-user tracking.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


POLAR_COMPANY_ID = 0x006B
POLAR_SERVICE_UUID = "feee"         # SIG-registered to Polar Electro Oy
POLAR_PFTP_UUID_SHORT = "feef"      # PFTP availability
GOPRO_PAIRING_UUID = "a5fe"         # indicates watch-paired-to-GoPro

POLAR_NAME_RE = re.compile(r"^Polar\s+(\S+(?:\s+\S+)*?)\s+([A-Za-z0-9]{6,10})$")


def _decode_user_id(mfr_payload: bytes) -> int | None:
    """Parse the Polar `PbMasterIdentifierBroadcast` and return the Flow user ID.

    Returns the BigInteger-decoded user ID, or None if this mfr payload doesn't
    match the PbMasterIdentifierBroadcast shape. 0 means FTU (unbonded).
    """
    if len(mfr_payload) < 5:
        return None
    sf = mfr_payload[2]
    # bits 4,5,6 must be set; bits 3,7 must be clear → 0x70..0x77.
    if (sf & 0xF8) != 0x70:
        return None
    user_id_len = mfr_payload[3]
    if user_id_len == 0 or len(mfr_payload) < 4 + user_id_len:
        return None
    user_id_bytes = mfr_payload[4:4 + user_id_len]
    # Parser reverses bytes then interprets as BigInteger.
    reversed_bytes = user_id_bytes[::-1]
    return int.from_bytes(reversed_bytes, "big", signed=False)


@register_parser(
    name="polar",
    company_id=POLAR_COMPANY_ID,
    service_uuid=POLAR_SERVICE_UUID,
    local_name_pattern=r"^Polar\s",
    description="Polar fitness trackers (H10, OH1, Verity Sense, Vantage, Grit X, etc.)",
    version="1.0.0",
    core=False,
)
class PolarParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        has_polar_company = (
            raw.manufacturer_data
            and len(raw.manufacturer_data) >= 2
            and int.from_bytes(raw.manufacturer_data[:2], "little") == POLAR_COMPANY_ID
        )
        has_polar_service = any(
            u.lower() in (POLAR_SERVICE_UUID, POLAR_PFTP_UUID_SHORT)
            for u in (raw.service_uuids or [])
        )
        name = raw.local_name or ""
        has_polar_name = name.startswith("Polar ")

        if not (has_polar_company or has_polar_service or has_polar_name):
            return None

        metadata: dict = {}
        if name:
            metadata["device_name"] = name
            m = POLAR_NAME_RE.match(name)
            if m:
                metadata["model_family"] = m.group(1)
                metadata["serial"] = m.group(2)

        user_id = None
        if has_polar_company:
            payload = raw.manufacturer_data[2:]
            metadata["mfr_payload_length"] = len(payload)
            # 13 bytes = watch, 11 bytes = HR strap / optical armband.
            if len(payload) == 13:
                metadata["product_tier_hint"] = "watch"
            elif len(payload) == 11:
                metadata["product_tier_hint"] = "strap_or_armband"
            user_id = _decode_user_id(payload)
            if user_id is not None:
                if user_id == 0:
                    metadata["pairing_state"] = "ftu"   # first-time-use / unbonded
                else:
                    metadata["pairing_state"] = "bonded"
                    metadata["flow_user_id"] = user_id

        if any(u.lower() == GOPRO_PAIRING_UUID for u in (raw.service_uuids or [])):
            metadata["gopro_paired"] = True

        if user_id and user_id > 0:
            id_basis = f"polar:flow_user:{user_id}"
        elif metadata.get("serial"):
            id_basis = f"polar:serial:{metadata['serial']}"
        else:
            id_basis = f"polar:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        raw_hex = raw.manufacturer_data[2:].hex() if raw.manufacturer_data and len(raw.manufacturer_data) > 2 else ""

        return ParseResult(
            parser_name="polar",
            beacon_type="polar",
            device_class="wearable",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )

    def storage_schema(self):
        return None
