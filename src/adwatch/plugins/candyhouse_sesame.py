"""CANDY HOUSE SESAME smart-lock family plugin.

Service UUID, product enum, and per-model device-ID extraction per
apk-ble-hunting/reports/candyhouse-sesame2_passive.md.

Lock state (locked/unlocked/battery) is NOT broadcast — connection required.
But the in-advertisement device-ID is stable, so a passive observer can
fingerprint and track a specific lock indefinitely.
"""

import base64
import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


SESAME_SERVICE_UUID = "fd81"

# Product model enum from CHProductModel (1-indexed, 34 known models).
PRODUCT_MODELS = {
    1: "WM2", 2: "Hub3", 3: "Hub3_LTE",
    4: "SS2", 5: "SS4",
    6: "SesameBot1", 7: "BiKeLock",
    8: "SS5", 9: "SS5PRO",
    10: "SSMOpenSensor",
    11: "SSMTouchPro", 12: "SSMTouch2Pro", 13: "SSMTouch", 14: "SSMTouch2",
    15: "BiKeLock2", 16: "BiKeLock3",
    17: "BLEConnector",
    18: "Remote", 19: "RemoteNano",
    20: "SS5US",
    21: "SesameBot2", 22: "SesameBot3",
    23: "SSMFace", 24: "SSMFace2", 25: "SSMFacePro", 26: "SSMFace2Pro",
    27: "SSMFaceAI", 28: "SSMFace2AI", 29: "SSMFaceProAI", 30: "SSMFace2ProAI",
    31: "SS6Pro", 32: "SS6ProSLiDingDoor",
    33: "SSMOpenSensor2", 34: "SSM_MIWA",
}

# Models where device-ID lives in the BLE local name (base64-decoded), not mfr-data.
_OS2_NAME_MODELS = {4, 5, 6, 7}  # SS2, SS4, SesameBot1, BiKeLock

# Hub3 family uses byte[1] for registration, others use byte[2].
_HUB3_MODELS = {2, 3}

# Per-model device-ID slice (start, length) within mfr-data after company-id prefix.
_DEVICE_ID_SLICES = {
    # WM2: bytes[3..11] (9 bytes)
    1: (3, 9),
    # Hub3 / Hub3_LTE: bytes[2..9] (8 bytes)
    2: (2, 8),
    3: (2, 8),
}
# All other in-advert models use bytes[3..18] (16 bytes) — populate dynamically.
for _m in PRODUCT_MODELS:
    if _m in _OS2_NAME_MODELS or _m in _DEVICE_ID_SLICES:
        continue
    _DEVICE_ID_SLICES[_m] = (3, 16)


@register_parser(
    name="candyhouse_sesame",
    service_uuid=SESAME_SERVICE_UUID,
    description="CANDY HOUSE SESAME smart locks (SS2/3/4/5/5PRO/Bot/Touch/Hub3/Face/etc.)",
    version="1.0.0",
    core=False,
)
class CandyHouseSesameParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        # SESAME doesn't use a SIG company ID — manufacturer_data is whatever
        # the device chose to put as its first record. We read from
        # manufacturer_payload (post-CID) to stay consistent with the framework's
        # split, then treat it as the SESAME mfr-data block.
        payload = raw.manufacturer_payload
        metadata: dict = {}
        device_id_hex: str | None = None

        if payload and len(payload) >= 1:
            model = payload[0]
            metadata["product_model_code"] = model
            metadata["product_model"] = PRODUCT_MODELS.get(model, f"UNKNOWN_{model}")

            # Registration bit + adv_tag_b1 (depends on model family).
            if len(payload) >= 3:
                if model in _HUB3_MODELS:
                    metadata["is_registered"] = bool(payload[1] & 0x01)
                else:
                    metadata["is_registered"] = bool(payload[2] & 0x01)
                    metadata["adv_tag_b1"] = bool(payload[2] & 0x02)

            # Device-ID extraction.
            if model in _OS2_NAME_MODELS and raw.local_name:
                # Base64-decode local name (with == padding restored).
                name = raw.local_name
                pad = "=" * (-len(name) % 4)
                try:
                    decoded = base64.b64decode(name + pad)
                    device_id_hex = decoded.hex()
                except Exception:
                    pass
            elif model in _DEVICE_ID_SLICES:
                start, length = _DEVICE_ID_SLICES[model]
                if len(payload) >= start + length:
                    device_id_hex = payload[start:start + length].hex()

            if device_id_hex:
                metadata["device_id_hex"] = device_id_hex

        if device_id_hex:
            id_basis = f"sesame:{device_id_hex}"
        else:
            id_basis = f"{raw.mac_address}:sesame"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        raw_hex = payload.hex() if payload else ""

        return ParseResult(
            parser_name="candyhouse_sesame",
            beacon_type="candyhouse_sesame",
            device_class="lock",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )

    def storage_schema(self):
        return None
