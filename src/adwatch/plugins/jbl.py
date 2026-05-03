"""JBL / Harman headphone & speaker plugin.

Per apk-ble-hunting/reports/jbl-stc-com_passive.md:

  - Manufacturer-data under company ID 0x0ECB (Harman) carries a
    2-byte big-endian product ID followed by 6 bytes of BD_ADDR.
  - Service-data under UUID 0xFDDF carries the same layout.
  - Avnera-silicon legacy accessories advertise service UUID
    58622534-68B7-4304-AEF2-0DE6F02E2018 (presence-only).

The embedded BD_ADDR is the persistent hardware MAC and survives BLE
random-address rotation — it's what we use for stable identity.
"""

import hashlib
import re

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import register_parser

JBL_SERVICE_UUID = "FDDF"
JBL_SERVICE_UUID_FULL = "0000fddf-0000-1000-8000-00805f9b34fb"
HARMAN_COMPANY_ID = 0x0ECB
AVNERA_SERVICE_UUID = "58622534-68b7-4304-aef2-0de6f02e2018"

JBL_NAME_RE = re.compile(r"^JBL (.+)")


def _decode_pid_and_bdaddr(payload: bytes) -> tuple[str | None, str | None]:
    """Decode (PID big-endian uint16, BD_ADDR colon-hex) from an 8+ byte payload."""
    if not payload or len(payload) < 8:
        return None, None
    pid = (payload[0] << 8) | payload[1]
    bd_addr = ":".join(f"{b:02X}" for b in payload[2:8])
    return f"{pid:04X}", bd_addr


@register_parser(
    name="jbl",
    company_id=HARMAN_COMPANY_ID,
    service_uuid=(JBL_SERVICE_UUID, AVNERA_SERVICE_UUID),
    local_name_pattern=r"^JBL ",
    description="JBL / Harman headphones & speakers",
    version="1.1.0",
    core=False,
)
class JblParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        uuid_match = (
            JBL_SERVICE_UUID_FULL in (raw.service_uuids or [])
            or AVNERA_SERVICE_UUID in (raw.service_uuids or [])
        )
        name_match = JBL_NAME_RE.match(raw.local_name) if raw.local_name else None
        fddf_sd = raw.service_data.get("fddf") if raw.service_data else None
        cid_match = raw.company_id == HARMAN_COMPANY_ID

        if not (uuid_match or name_match or fddf_sd is not None or cid_match):
            return None

        metadata: dict = {}
        if name_match:
            metadata["model"] = name_match.group(1)
            metadata["device_name"] = raw.local_name

        # Avnera-silicon legacy accessory presence-only signal.
        if AVNERA_SERVICE_UUID in (raw.service_uuids or []):
            metadata["avnera_silicon"] = True

        # PID + BD_ADDR extraction. Mfr-data and FDDF service-data share the
        # same 8-byte layout per the report.
        pid_hex = bd_addr = None
        if cid_match and raw.manufacturer_payload:
            pid_hex, bd_addr = _decode_pid_and_bdaddr(raw.manufacturer_payload)
        if pid_hex is None and fddf_sd:
            pid_hex, bd_addr = _decode_pid_and_bdaddr(fddf_sd)

        if pid_hex:
            metadata["product_id"] = pid_hex
        if bd_addr:
            metadata["bd_addr"] = bd_addr

        # Find My Device Network co-presence (some JBL models broadcast FE2C).
        if raw.service_data and raw.service_data.get("fe2c"):
            metadata["has_fmdn"] = True

        # Stable identity prefers the embedded BD_ADDR over the rotating BLE MAC.
        if bd_addr:
            id_basis = f"jbl:{bd_addr}"
        else:
            id_basis = f"jbl:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        raw_hex = raw.manufacturer_data.hex() if raw.manufacturer_data else ""

        return ParseResult(
            parser_name="jbl",
            beacon_type="jbl",
            device_class="speaker",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )

    def storage_schema(self):
        return None
