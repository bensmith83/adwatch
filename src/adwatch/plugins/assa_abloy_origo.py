"""ASSA ABLOY / HID Global Origo Mobile Access plugin.

Per apk-ble-hunting/reports/assaabloy-mobileaccess_passive.md:

  - Per-deployment 128-bit service UUID `00009800-0000-1000-8000-00177A<24bit>`
    where the OUI `00:17:7A` is ASSA ABLOY's IEEE block. Match by prefix.
  - Reader/phone HID-Global mfr-data under company_id `0x012E` (302) carrying
    opening-type capability bitmask + RSSI thresholds.
  - Phone iBeacon under Apple `0x004C` with the deployment UUID as proximity
    UUID — the 4-byte major/minor is a stable per-enrollment credential ref.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


HID_GLOBAL_COMPANY_ID = 0x012E
APPLE_COMPANY_ID = 0x004C

# Per-deployment UUID prefix — first 13 bytes are constant; last 3 bytes vary.
ORIGO_UUID_RE = re.compile(
    r"^00009800-0000-1000-8000-00177a[0-9a-f]{6}$", re.IGNORECASE
)

OPENING_TYPE_BITS = {
    0: "PROXIMITY",
    1: "MOTION",
    2: "SEAMLESS",
    3: "APPLICATION_SPECIFIC",
    6: "PROXIMITY_ENHANCED",
}


def _decode_hid_mfr(payload: bytes) -> dict:
    """Decode the HID-Global mfr-data frame (post-CID strip).

    Layout per the reader/phone passive analysis:
      [0..1]  echoed mfr-id 0x012E (big-endian)
      [2]     upper nibble = protocol version (only 1 supported), lower = trigger-block length N
      [3..3+N] trigger block (opaque)
      [3+N]   communication profile version
      [3+N+1] opening-type bitmask
      [3+N+2..] RSSI thresholds (2-4 of them)
    """
    md: dict = {}
    if len(payload) < 4:
        return md
    md["protocol_version"] = (payload[2] >> 4) & 0x0F
    n = payload[2] & 0x0F
    if len(payload) < 3 + n + 2:
        return md
    md["trigger_block_hex"] = payload[3:3 + n].hex()
    cursor = 3 + n
    md["profile_version"] = payload[cursor]
    cursor += 1
    bitmask = payload[cursor]
    cursor += 1
    md["opening_type_bitmask"] = bitmask
    md["opening_types"] = [
        OPENING_TYPE_BITS[bit]
        for bit in OPENING_TYPE_BITS
        if (bitmask >> bit) & 0x01
    ]
    md["credential_unavailable"] = bool(bitmask & 0x80)
    # Up to 4 RSSI thresholds (signed bytes).
    thresholds = []
    while cursor < len(payload) and len(thresholds) < 4:
        b = payload[cursor]
        thresholds.append(b - 256 if b >= 128 else b)
        cursor += 1
    threshold_names = ["seamless", "proximity", "motion", "enhanced"]
    for name, value in zip(threshold_names, thresholds):
        md[f"rssi_threshold_{name}"] = value
    return md


def _decode_ibeacon_phone(payload: bytes) -> dict | None:
    """Decode an iBeacon frame whose proximity UUID matches the Origo template.

    Returns metadata if the iBeacon fits the Origo phone-broadcast shape, else None.
    """
    # iBeacon: [0]=0x02, [1]=0x15, [2..17]=UUID, [18..21]=major+minor, [22]=tx
    if len(payload) < 23 or payload[0] != 0x02 or payload[1] != 0x15:
        return None
    proximity_bytes = payload[2:18]
    # iBeacon UUID is on the wire in big-endian (RFC4122) order; render directly.
    uuid_str = (
        f"{proximity_bytes[0:4].hex()}-{proximity_bytes[4:6].hex()}-"
        f"{proximity_bytes[6:8].hex()}-{proximity_bytes[8:10].hex()}-"
        f"{proximity_bytes[10:16].hex()}"
    )
    if not ORIGO_UUID_RE.match(uuid_str):
        return None
    return {
        "ibeacon_proximity_uuid": uuid_str,
        "deployment_code_hex": uuid_str[-6:],
        "ibeacon_major_minor_hex": payload[18:22].hex(),
        "ibeacon_tx_power": payload[22] - 256 if payload[22] >= 128 else payload[22],
    }


@register_parser(
    name="assa_abloy_origo",
    company_id=(HID_GLOBAL_COMPANY_ID, APPLE_COMPANY_ID),
    description="ASSA ABLOY / HID Global Origo Mobile Access (enterprise)",
    version="1.0.0",
    core=False,
)
class AssaAbloyOrigoParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        origo_uuids = [u for u in normalized if ORIGO_UUID_RE.match(u)]
        cid = raw.company_id
        payload = raw.manufacturer_payload

        # Apple-CID gating: must be an Origo iBeacon, not just any iBeacon.
        ibeacon_md = None
        if cid == APPLE_COMPANY_ID and payload:
            ibeacon_md = _decode_ibeacon_phone(payload)

        hid_md = None
        if cid == HID_GLOBAL_COMPANY_ID and payload:
            hid_md = _decode_hid_mfr(payload)

        if not (origo_uuids or ibeacon_md or hid_md):
            return None

        metadata: dict = {}

        if origo_uuids:
            uuid = origo_uuids[0]
            metadata["origo_service_uuid"] = uuid
            metadata["deployment_code_hex"] = uuid[-6:]
            metadata["role"] = "reader_or_phone"

        if ibeacon_md:
            metadata.update(ibeacon_md)
            metadata["role"] = "phone"

        if hid_md:
            metadata.update(hid_md)
            # Reader and phone both can emit the HID frame — leave role as-is.

        if raw.local_name:
            metadata["device_name"] = raw.local_name

        # Identity prefers the major/minor (stable per-enrollment credential ref).
        if ibeacon_md:
            id_basis = f"origo:phone:{ibeacon_md['ibeacon_major_minor_hex']}"
        elif metadata.get("deployment_code_hex"):
            id_basis = f"origo:{metadata['deployment_code_hex']}:{raw.mac_address}"
        else:
            id_basis = f"origo:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        raw_hex = payload.hex() if payload else ""

        return ParseResult(
            parser_name="assa_abloy_origo",
            beacon_type="assa_abloy_origo",
            device_class="access_control",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )

    def storage_schema(self):
        return None
