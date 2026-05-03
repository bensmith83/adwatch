"""Tandem t:slim X2 insulin pump + Abbott FreeStyle Libre 3 (paired CGM) plugin.

Per apk-ble-hunting/reports/tandemdiabetes-tconnect_passive.md:

  - Tandem t:slim X2 pump: SIG service UUID 0xFDFB (Tandem-allocated).
  - Abbott Libre 3 CGM (Tandem integration): SIG service UUID 0xFDE3 +
    name `^ABBOTT<serial>`. Serial in name is stable per-sensor.

SAFETY-CRITICAL: identifying this advertisement = Type-1 diabetic on
hybrid-closed-loop therapy. Passive observation only — never connect.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


TANDEM_PUMP_UUID = "fdfb"  # SIG-assigned Tandem
LIBRE3_UUID = "fde3"       # SIG-assigned Abbott (legacy Tandem-CGM, repurposed)
ABBOTT_NAME_RE = re.compile(r"^ABBOTT([A-Za-z0-9]+)$")


@register_parser(
    name="tandem_pump",
    service_uuid=(TANDEM_PUMP_UUID, LIBRE3_UUID),
    local_name_pattern=r"^ABBOTT",
    description="Tandem t:slim X2 insulin pump + Libre 3 CGM (paired)",
    version="1.0.0",
    core=False,
)
class TandemPumpParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        pump_hit = TANDEM_PUMP_UUID in normalized
        cgm_hit = LIBRE3_UUID in normalized
        name_match = ABBOTT_NAME_RE.match(raw.local_name) if raw.local_name else None

        if not (pump_hit or cgm_hit or name_match):
            return None

        metadata: dict = {}

        if pump_hit:
            metadata["device_kind"] = "tslim_x2_pump"
            metadata["safety_critical"] = True

        if cgm_hit or name_match:
            metadata["device_kind"] = "libre3_cgm"
            metadata["safety_critical"] = True
            if name_match:
                metadata["sensor_serial"] = name_match.group(1)

        # Both UUIDs together → user is on hybrid-closed-loop therapy.
        if pump_hit and (cgm_hit or name_match):
            metadata["therapy_mode"] = "hybrid_closed_loop"

        # Identity prefers sensor serial (stable across MAC rotation for the
        # full 14-day Libre 3 lifespan).
        if name_match:
            id_basis = f"libre3:{name_match.group(1)}"
        elif pump_hit:
            id_basis = f"tslim:{raw.mac_address}"
        else:
            id_basis = f"libre3:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="tandem_pump",
            beacon_type="tandem_pump",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
