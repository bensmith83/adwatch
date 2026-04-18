"""MEATER wireless meat thermometer plugin.

Parsing paths per apk-ble-hunting/reports/apptionlabs-meater-app_passive.md.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import _normalize_uuid, register_parser


MEATER_COMPANY_ID = 0x037B

# Probe service UUIDs — any indicates a MEATER probe or range extender.
PROBE_SERVICE_UUIDS = (
    "a75cc7fc-c956-488f-ac2a-2dbc08b63a04",  # V1 probe
    "dcbb67ca-64fb-41a3-99d1-5d9fd8cf33ca",  # V2 probe (flag-gated)
    "c9e2746c-59f1-4e54-a0dd-e1e54555cf8b",  # MEATER+ V2 probe
    "49141a23-307f-4e25-ad82-0a3f00d8b90b",  # MEATER+ SE probe
)

# Normal Block advertisement — 8-byte mfr payload: device_id only, product=BLOCK.
BLOCK_NORMAL_UUID = "097f9db4-be9b-43c0-931d-51a6599ff70d"

# Keep-alive / Gen2 / Gen3 Block UUIDs — 10-byte mfr payload:
# product_type(1) + device_id(8) + status_mode(1).
BLOCK_KEEPALIVE_UUIDS = (
    "24b299d9-61f7-48ba-86e0-f459dad3fc87",  # keep-alive
    "b7107bbe-da2a-4124-b2cc-aafd624b61ce",  # Gen2 block
    "9e09e66c-78dc-4e28-80c3-f7eb5194daaf",  # Gen3 block (1x Gen1)
    "407c0a68-6538-4af6-8c41-c9fa02114295",  # Gen3 block (1x Gen2)
    "88821f85-4af5-425f-96e4-63e6aac2e097",  # Gen3 block (2x Gen1)
    "7cf05643-1430-4be6-a0a8-b1e2d95462ba",  # Gen3 block (2x Gen2)
)

PRODUCT_TYPES = {
    0: "PROBE",
    1: "BLOCK_PROBE_ONE",
    2: "BLOCK_PROBE_TWO",
    3: "BLOCK_PROBE_THREE",
    4: "BLOCK_PROBE_FOUR",
    5: "THERMOMIX_PROBE",
    6: "TRAEGER_PROBE",
    8: "BLOCK",
    16: "SECOND_GENERATION_PROBE",
    17: "SECOND_GENERATION_BLOCK_PROBE_ONE",
    18: "SECOND_GENERATION_BLOCK_PROBE_TWO",
    19: "SECOND_GENERATION_BLOCK_PROBE_THREE",
    20: "SECOND_GENERATION_BLOCK_PROBE_FOUR",
    21: "SECOND_GENERATION_THERMOMIX_PROBE",
    22: "SECOND_GENERATION_TRAEGER_PROBE",
    64: "AMBER",
    80: "SECOND_GENERATION_THERMOMIX_PLUS",
    112: "SECOND_GENERATION_PLUS",
    113: "SECOND_GENERATION_PLUS_PRO",
    128: "PLUS",
    129: "PLUS_SE",
    144: "SECOND_GENERATION_TRAEGER_PLUS",
    162: "SECOND_GENERATION_TWO_PROBE_BLOCK",
    164: "SECOND_GENERATION_FOUR_PROBE_BLOCK",
    177: "THIRD_GENERATION_ONE_FIRST_GEN_PROBE_BLOCK",
    178: "THIRD_GENERATION_TWO_FIRST_GEN_PROBE_BLOCK",
    179: "THIRD_GENERATION_ONE_SECOND_GEN_PROBE_BLOCK",
    180: "THIRD_GENERATION_TWO_SECOND_GEN_PROBE_BLOCK",
}

BLOCK_STATUS_MODES = {
    5: "Booting",
    6: "Selecting",
    7: "Standalone",
    8: "Configuring",
    9: "WiFi Client",
    10: "WiFi AP",
    11: "WiFi AP OTA",
    12: "Probe Pairing",
    13: "Battery Empty",
    14: "Battery Empty (USB)",
    15: "WiFi Client OTA",
}


_NORMALIZED_PROBE_UUIDS = frozenset(_normalize_uuid(u) for u in PROBE_SERVICE_UUIDS)
_NORMALIZED_BLOCK_NORMAL = _normalize_uuid(BLOCK_NORMAL_UUID)
_NORMALIZED_BLOCK_KEEPALIVE = frozenset(_normalize_uuid(u) for u in BLOCK_KEEPALIVE_UUIDS)

_ALL_MEATER_UUIDS = [BLOCK_NORMAL_UUID, *BLOCK_KEEPALIVE_UUIDS, *PROBE_SERVICE_UUIDS]

_NAME_FALLBACK_RE = re.compile(r"^([0-9a-fA-F]{2})-([0-9a-fA-F]+)$")


@register_parser(
    name="meater",
    company_id=MEATER_COMPANY_ID,
    service_uuid=_ALL_MEATER_UUIDS,
    local_name_pattern=r"^MEATER|^[0-9a-fA-F]{2}-[0-9a-fA-F]+$",
    description="MEATER wireless meat thermometer",
    version="1.1.0",
    core=False,
)
class MEATERParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        metadata: dict = {}
        device_id_int = None

        path = self._select_path(raw)
        payload = raw.manufacturer_payload

        if path == "block_normal" and payload and len(payload) >= 8:
            device_id_int = int.from_bytes(payload[:8], "little")
            metadata["product_type_code"] = 8
            metadata["product_type"] = PRODUCT_TYPES.get(8, "UNKNOWN")
            metadata["device_id"] = device_id_int
            metadata["device_id_hex"] = payload[:8][::-1].hex()

        elif path == "block_keepalive" and payload and len(payload) >= 10:
            pt = payload[0]
            device_id_int = int.from_bytes(payload[1:9], "little")
            status = payload[9]
            metadata["product_type_code"] = pt
            metadata["product_type"] = PRODUCT_TYPES.get(pt, f"UNKNOWN_{pt}")
            metadata["device_id"] = device_id_int
            metadata["device_id_hex"] = payload[1:9][::-1].hex()
            metadata["status_mode_code"] = status
            metadata["status_mode"] = BLOCK_STATUS_MODES.get(status, f"UNKNOWN_{status}")

        elif path == "probe" and payload and len(payload) >= 9:
            pt = payload[0]
            device_id_int = int.from_bytes(payload[1:9], "little")
            metadata["product_type_code"] = pt
            metadata["product_type"] = PRODUCT_TYPES.get(pt, f"UNKNOWN_{pt}")
            metadata["device_id"] = device_id_int
            metadata["device_id_hex"] = payload[1:9][::-1].hex()

        # Name fallback: <hex_product_type>-<hex_device_id>
        if device_id_int is None:
            m = _NAME_FALLBACK_RE.match(raw.local_name or "")
            if m:
                pt = int(m.group(1), 16)
                metadata["product_type_code"] = pt
                metadata["product_type"] = PRODUCT_TYPES.get(pt, f"UNKNOWN_{pt}")
                metadata["device_id_hex"] = m.group(2).lower()

        if device_id_int is not None:
            id_basis = f"meater:{device_id_int}"
        else:
            id_basis = f"{raw.mac_address}:MEATER"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        raw_hex = payload.hex() if payload else ""

        return ParseResult(
            parser_name="meater",
            beacon_type="meater",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )

    @staticmethod
    def _select_path(raw):
        if not raw.service_uuids:
            return "probe"  # default when only mfr data present
        normalized = [_normalize_uuid(u) for u in raw.service_uuids]
        if _NORMALIZED_BLOCK_NORMAL in normalized:
            return "block_normal"
        for u in normalized:
            if u in _NORMALIZED_BLOCK_KEEPALIVE:
                return "block_keepalive"
        for u in normalized:
            if u in _NORMALIZED_PROBE_UUIDS:
                return "probe"
        return "probe"

    def storage_schema(self):
        return None
