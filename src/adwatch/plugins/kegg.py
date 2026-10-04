"""kegg fertility tracker / kegel trainer plugin.

Per apk-ble-hunting/reports/ladytechnologies-kegel_passive.md.

Discovery: exact local name ``kegg``. The app reads ABSOLUTE offsets 15-18 of
``ScanRecord.getBytes()`` (battery %, measurementStatus enum, deviceStatus
enum, buffered-measurement count) without walking AD structures; the CID and
containing AD element are unknown. Assuming the most probable framing the
report describes (Flags + Name "kegg" + manufacturer-specific data), absolute
byte 15 = 3rd byte of the mfr payload after the CID = ``manufacturer_payload[2]``.
Decoded values are range-checked and flagged ``layout_assumed`` — needs a
live capture to confirm.

Identity = MAC (no in-payload id). Flagged ``sensitive=True``: the
measurement status broadcasts whether the intravaginal sensor is inserted.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


KEGG_NAME_PATTERN = r"^kegg$"

MEASUREMENT_STATUS = {
    0: "READY",
    1: "INSERT_TIMER_RUNNING",
    2: "INSERTED",
    3: "WAITING_TO_BE_INSERTED",
    4: "PS_TIMER_RUNNING",
    5: "PROGRAM_SEQUENCE_EXECUTING",
    6: "PROGRAM_SEQUENCE_FINISHED",
    7: "INSERT_TIMED_OUT",
    8: "SENDING_DATA",
    9: "PROGRAM_SEQUENCE_FINISHED_WITH_AVRG_RESISTIVITY_OOR",
    10: "PROGRAM_SEQUENCE_FINISHED_WITH_WRONG_NUMBER_OF_MEASUREMENTS",
    11: "PS_FINISHED_WITH_AVRG_RESISTIVITY_OOR_AND_WRONG_NUM_OF_MEAS",
}

DEVICE_STATUS = {
    0: "ALL_GOOD",
    1: "CHARGING",
    2: "CHARGING_FINISHED",
    3: "BATTERY_LOW",
    4: "OPERATING_TOO_LONG",
    5: "BATTERY_NOT_CHARGING",
    6: "POWER_FAULT",
    7: "NRF_FAULT",
    8: "ELECTRODES_FAULT",
    9: "CHARGER_TIMER_TIMEOUT",
    10: "CHARGER_FAULT",
    11: "CHARGING_TEMPERATURE_HIGH",
    12: "WDT_RESET",
    13: "OTHER_FAULT",
}

# Absolute ScanRecord offset 15 -> manufacturer_payload index under the
# assumed Flags(3) + Name"kegg"(6) + MfrAD-header(2) + CID(2) framing.
_STATUS_OFFSET = 2


@register_parser(
    name="kegg",
    local_name_pattern=KEGG_NAME_PATTERN,
    description="kegg fertility tracker / kegel trainer (name + status block)",
    version="1.0.0",
    core=False,
)
class KeggParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if (raw.local_name or "") != "kegg":
            return None

        metadata: dict = {
            "vendor": "kegg",
            "product": "kegg fertility tracker",
            "sensitive": True,
            "sensitive_category": "reproductive_health",
        }
        mfr = raw.manufacturer_data
        if mfr:
            metadata["mfr_data_hex"] = mfr.hex()
            if raw.company_id is not None:
                metadata["mfr_company_id"] = raw.company_id

        payload = raw.manufacturer_payload or b""
        block = payload[_STATUS_OFFSET:_STATUS_OFFSET + 4]
        if len(block) == 4:
            batt, ms, ds, buf = block
            if batt <= 100 and ms in MEASUREMENT_STATUS and ds in DEVICE_STATUS:
                metadata.update({
                    "battery_percent": batt,
                    "measurement_status_code": ms,
                    "measurement_status": MEASUREMENT_STATUS[ms],
                    "device_status_code": ds,
                    "device_status": DEVICE_STATUS[ds],
                    "buffered_measurements": buf,
                    "layout_assumed": True,
                })

        id_hash = hashlib.sha256(f"kegg:{raw.mac_address}".encode()).hexdigest()[:16]
        return ParseResult(
            parser_name="kegg",
            beacon_type="kegg",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
