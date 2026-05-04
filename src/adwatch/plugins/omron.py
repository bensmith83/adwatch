"""Omron HealthCare BP/scale/oximeter/glucose plugin.

Per apk-ble-hunting/reports/omronhealthcare-omronconnect_passive.md:

  - Omron company_id 0x020E (526). Frame Data Type 0x01 = "EachUserData".
  - SIG service UUIDs per product class: 0x1810 BP / 0x1808 Glucose /
    0x1809 Thermometer / 0x181D Weight Scale / 0x181B Body Composition.
  - Custom 128-bit oximeter UUID 6E400001-B5A3-F393-EFA9-E50E24DCCA9E.
  - Local name: ^BLE[sS]mart_<model:4hex><subtype:4hex><serial-tail>.

EachUserData mfr payload:
  [0]   data_type tag (must == 0x01)
  [1]   flags: bits0-1=numUsers-1, bit2=time_not_set, bit3=pairing_mode,
        bit5=bluetooth_standard_mode
  [2..] per-user (lastSeqNumber:u16le, numberOfRecords:u8) repeated numUsers times
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


OMRON_COMPANY_ID = 0x020E
OMRON_HEALTHCARE_OFFICIAL_CID = 0x0105

OMRON_OXIMETER_UUID = "6e400001-b5a3-f393-efa9-e50e24dcca9e"

# SIG profile UUIDs Omron devices commonly advertise.
OMRON_SIG_UUIDS = (
    "1810",  # Blood Pressure
    "1808",  # Glucose
    "1809",  # Health Thermometer
    "181d",  # Weight Scale
    "181b",  # Body Composition
    "1822",  # Pulse Oximeter
)

_NAME_RE = re.compile(
    r"^BLE[sS]mart_([0-9a-fA-F]{4})([0-9a-fA-F]{4})([0-9a-fA-F]*)"
)


@register_parser(
    name="omron",
    company_id=(OMRON_COMPANY_ID, OMRON_HEALTHCARE_OFFICIAL_CID),
    service_uuid=(*OMRON_SIG_UUIDS, OMRON_OXIMETER_UUID),
    local_name_pattern=r"^BLE[sS]mart_",
    description="Omron HealthCare devices (BP, scale, glucose, thermometer, oximeter)",
    version="1.0.0",
    core=False,
)
class OmronParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        sig_match = [u for u in OMRON_SIG_UUIDS if u in normalized]
        oxi_hit = OMRON_OXIMETER_UUID in normalized
        cid_hit = raw.company_id in (OMRON_COMPANY_ID, OMRON_HEALTHCARE_OFFICIAL_CID)
        name_match = _NAME_RE.match(raw.local_name) if raw.local_name else None

        if not (sig_match or oxi_hit or cid_hit or name_match):
            return None

        metadata: dict = {}

        # Product class hint from matched SIG UUID.
        sig_to_class = {
            "1810": "blood_pressure_monitor",
            "1808": "glucose_meter",
            "1809": "thermometer",
            "181d": "weight_scale",
            "181b": "body_composition_scale",
            "1822": "pulse_oximeter",
        }
        if sig_match:
            metadata["product_class"] = sig_to_class[sig_match[0]]
            metadata["sig_service_uuid"] = sig_match[0]
        elif oxi_hit:
            metadata["product_class"] = "pulse_oximeter"
            metadata["sig_service_uuid"] = OMRON_OXIMETER_UUID

        # Name-encoded model + subtype.
        if name_match:
            metadata["model_code_hex"] = name_match.group(1).lower()
            metadata["subtype_code_hex"] = name_match.group(2).lower()
            metadata["serial_tail_hex"] = name_match.group(3).lower()
            metadata["device_name"] = raw.local_name

        # EachUserData mfr decode (only for company 0x020E).
        if raw.company_id == OMRON_COMPANY_ID:
            payload = raw.manufacturer_payload
            if payload and len(payload) >= 2 and payload[0] == 0x01:
                flags = payload[1]
                num_users = (flags & 0x03) + 1
                metadata["data_type"] = "EachUserData"
                metadata["number_of_users"] = num_users
                metadata["is_time_not_set"] = bool(flags & 0x04)
                metadata["is_pairing_mode"] = bool(flags & 0x08)
                metadata["is_bluetooth_standard_mode"] = bool(flags & 0x20)
                users = []
                for i in range(num_users):
                    base = 2 + i * 3
                    if base + 3 > len(payload):
                        break
                    seq = int.from_bytes(payload[base:base + 2], "little")
                    nrec = payload[base + 2]
                    users.append({"last_sequence_number": seq, "number_of_records": nrec})
                if users:
                    metadata["users"] = users

        # Identity hash: prefer the in-name serial tail (stable across MAC rotation).
        if name_match and name_match.group(3):
            id_basis = f"omron:{name_match.group(1).lower()}:{name_match.group(3).lower()}"
        else:
            id_basis = f"omron:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]
        raw_hex = raw.manufacturer_data.hex() if raw.manufacturer_data else ""

        return ParseResult(
            parser_name="omron",
            beacon_type="omron",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )

    def storage_schema(self):
        return None
