"""PLAUD AI recorder BLE advertisement parser.

Supports PLAUD NOTE / NotePin / NotePin S / Note Pro. These AI voice
recorders advertise an identity beacon in manufacturer-specific data.

Manufacturer payload layout (apk-ble-hunting plaud-android-plaud report,
``ri/l.java:122-260``). The app reads ``getManufacturerSpecificData()`` at
``keyAt(0)`` — i.e. the CID-stripped value — so offsets map 1:1 onto
adwatch's ``manufacturer_payload``. The company ID is device-supplied (not a
constant in the app); observed captures use 0x0059 and 0x005D.

    [len1][model_id LE (len1 bytes)]      optional; absent on NotePin capture
    [len2]['V'][version LE (len2-1 bytes)]
    [namelen][serial bytes (namelen)]     hex-rendered; first 3 digits = product

Integers are little-endian (native ``libtnt_ble_utils`` readInt; the NOTE
capture's model_id 0x0378 == 888 == its product code confirms). The passive
report's "big-endian" claim is wrong.
"""

import hashlib
import re

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import register_parser

PLAUD_NAME_RE = re.compile(r"^PLAUD[\s_](\S+)")
PLAUD_COMPANY_IDS = [0x0059, 0x005D]

PRODUCT_CODES = {
    "880": "Plaud NotePin",
    "882": "Plaud NotePin S",
    "888": "Plaud Note",
    "881": "Plaud Note Pro",
    "883": "Plaud Note Pro",
}


def _decode_mfr(payload: bytes) -> dict:
    """Walk the length-prefixed records. Returns whatever fields decoded."""
    out: dict = {}
    pos = 0
    n = len(payload)
    # Optional model-id record: present unless the first record is the 'V' one.
    if pos + 1 < n and payload[pos + 1] != ord("V"):
        ln = payload[pos]
        if ln < 1 or pos + 1 + ln > n:
            return out
        out["model_id"] = int.from_bytes(payload[pos + 1:pos + 1 + ln], "little")
        pos += 1 + ln
    # Version record
    if pos + 2 > n:
        return out
    ln = payload[pos]
    if ln < 2 or pos + 1 + ln > n or payload[pos + 1] != ord("V"):
        return out
    out["version_char"] = "V"
    out["version_number"] = int.from_bytes(payload[pos + 2:pos + 1 + ln], "little")
    pos += 1 + ln
    # Serial / name record
    if pos >= n:
        return out
    ln = payload[pos]
    if ln < 2 or pos + 1 + ln > n:
        return out
    serial = payload[pos + 1:pos + 1 + ln].hex()
    out["serial"] = serial
    code = serial[:3]
    if code in PRODUCT_CODES:
        out["product_code"] = code
        out["product"] = PRODUCT_CODES[code]
    return out


@register_parser(
    name="plaud",
    company_id=PLAUD_COMPANY_IDS,
    local_name_pattern=r"^PLAUD[\s_]",
    description="PLAUD AI recorder advertisements",
    version="1.1.0",
    core=False,
)
class PlaudParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        m = PLAUD_NAME_RE.match(raw.local_name) if raw.local_name else None

        decoded: dict = {}
        payload = raw.manufacturer_payload
        if payload:
            decoded = _decode_mfr(payload)

        # Without a PLAUD name, require the full shape incl. known product code
        # (CIDs 0x0059/0x005D are shared with many other vendors).
        if not m and "product" not in decoded:
            return None

        serial = decoded.get("serial") if "product" in decoded else None
        id_basis = serial if serial else raw.mac_address
        id_hash = hashlib.sha256(f"plaud:{id_basis}".encode()).hexdigest()[:16]

        metadata: dict = {}
        if m:
            metadata["device_name"] = raw.local_name
            metadata["model"] = m.group(1)
        else:
            metadata["model"] = decoded["product"]
        metadata.update(decoded)

        if raw.manufacturer_data and len(raw.manufacturer_data) >= 2:
            metadata["company_id"] = raw.company_id

        raw_hex = raw.manufacturer_data.hex() if raw.manufacturer_data else ""

        return ParseResult(
            parser_name="plaud",
            beacon_type="plaud",
            device_class="recorder",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )
