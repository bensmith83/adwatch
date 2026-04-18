"""Fitbit fitness tracker plugin.

Fitbit's companion app has **no manufacturer-data or service-data parsing**
anywhere — all protocol action happens post-connect via the Golden Gate
Gattlink native layer. So for passive detection the reliable signals are:

- SIG service UUID 0xFD62 (Fitbit, Inc.) — primary production identifier
- 128-bit Gattlink UUID ABBAFF00-E56A-484C-B832-8B17CF6CBFE8 — dev-kit /
  pre-SIG-registration firmware
- Aria scale UUID 26F33A00-52A8-414B-99A2-1DB75C99C032
- Local name prefixes (Sense, Versa, Charge, Inspire, Luxe, Ace, Aria)

Fitbit's SIG company ID is 0x0038 per the Bluetooth SIG list; the companion
app never references it, and static analysis found no evidence of mfr-data
emission. Source: apk-ble-hunting/reports/fitbit-fitbitmobile_passive.md.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import _normalize_uuid, register_parser


FITBIT_COMPANY_ID = 0x0038                       # SIG-registered, not emitted in Java-observable flows.
FITBIT_SERVICE_UUID_SIG = "fd62"                 # 16-bit SIG production identifier.
FITBIT_GATTLINK_UUID = "abbaff00-e56a-484c-b832-8b17cf6cbfe8"
FITBIT_ARIA_UUID = "26f33a00-52a8-414b-99a2-1db75c99c032"

# Legacy speculation kept for backward compatibility with existing tests/
# downstream consumers. The companion app does not parse mfr data, so any
# interpretation here is best-effort from historical captures.
QUALCOMM_COMPANY_ID = 0x000A
KNOWN_OPCODES = {0x01: "advertisement", 0x02: "pairing_request", 0x06: "status"}

_FITBIT_NAME_RE = re.compile(
    r"(?i)^(Fitbit|Charge|Versa|Sense|Inspire|Luxe|Ace|Aria)"
)


@register_parser(
    name="fitbit",
    company_id=QUALCOMM_COMPANY_ID,
    service_uuid=[FITBIT_SERVICE_UUID_SIG, FITBIT_GATTLINK_UUID, FITBIT_ARIA_UUID],
    local_name_pattern=_FITBIT_NAME_RE.pattern,
    description="Fitbit fitness trackers",
    version="1.1.0",
    core=False,
)
class FitbitParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        is_fitbit_name = bool(raw.local_name and _FITBIT_NAME_RE.match(raw.local_name))

        has_fitbit_uuid = False
        is_aria = False
        for u in (raw.service_uuids or []):
            n = _normalize_uuid(u)
            if n == _normalize_uuid(FITBIT_SERVICE_UUID_SIG) or n == _normalize_uuid(FITBIT_GATTLINK_UUID):
                has_fitbit_uuid = True
            if n == _normalize_uuid(FITBIT_ARIA_UUID):
                has_fitbit_uuid = True
                is_aria = True

        has_qualcomm_mfr = (
            raw.manufacturer_data
            and len(raw.manufacturer_data) >= 4
            and int.from_bytes(raw.manufacturer_data[:2], "little") == QUALCOMM_COMPANY_ID
        )

        if not (is_fitbit_name or has_fitbit_uuid or has_qualcomm_mfr):
            return None

        metadata: dict = {}
        if raw.local_name:
            metadata["device_name"] = raw.local_name
        if has_fitbit_uuid:
            metadata["has_fitbit_service_uuid"] = True
        if is_aria:
            metadata["product_line"] = "Aria"
        elif is_fitbit_name:
            # Classify by name prefix for quick downstream filtering.
            m = _FITBIT_NAME_RE.match(raw.local_name)
            metadata["product_line"] = m.group(1).title() if m else None

        payload_hex = ""
        if has_qualcomm_mfr:
            payload = raw.manufacturer_data[2:]
            payload_hex = payload.hex()
            opcode = payload[0]
            # Known-opcode gate only applies when we'd otherwise have no
            # other Fitbit signal — avoids false positives on random 0x000A
            # ads.
            if not is_fitbit_name and not has_fitbit_uuid and opcode not in KNOWN_OPCODES:
                return None
            metadata["airlink_opcode"] = opcode
            metadata["airlink_state"] = KNOWN_OPCODES.get(opcode, f"unknown_0x{opcode:02x}")
            if len(payload) >= 2:
                metadata["device_type"] = payload[1]

        id_hash = hashlib.sha256(f"{raw.mac_address}:fitbit".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="fitbit",
            beacon_type="fitbit",
            device_class="wearable",
            identifier_hash=id_hash,
            raw_payload_hex=payload_hex,
            metadata=metadata,
        )
