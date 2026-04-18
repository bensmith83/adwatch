"""Dexcom Continuous Glucose Monitor (CGM) BLE advertisement parser.

Dexcom G6 and G7 transmitters advertise passively with distinct identifiers:

- G6: SIG service UUID 0xFEBC (Dexcom, Inc.) + local name `Dexcom<XX>` where
  `<XX>` is the last two characters of the printed transmitter serial
  (apk-ble-hunting/reports/dexcom-g6_passive.md).
- G7: community-documented service UUID f8083532-849e-531c-c594-30f1f86a4ea5
  + local name prefix `DXCM` (R8-obfuscated in the APK, see
  apk-ble-hunting/reports/dexcom-g7_passive.md).
"""

import hashlib
import re

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import _normalize_uuid, register_parser


DEXCOM_G6_SERVICE_UUID = "febc"
DEXCOM_G7_SERVICE_UUID = "f8083532-849e-531c-c594-30f1f86a4ea5"
DEVICE_INFO_UUID = "180a"

_G6_NAME_RE = re.compile(r"^Dexcom([A-Z0-9]{2})$")
_G7_NAME_RE = re.compile(r"^DXCM")

_G6_NORMALIZED = _normalize_uuid(DEXCOM_G6_SERVICE_UUID)
_G7_NORMALIZED = _normalize_uuid(DEXCOM_G7_SERVICE_UUID)


@register_parser(
    name="dexcom_cgm",
    service_uuid=[DEXCOM_G6_SERVICE_UUID, DEXCOM_G7_SERVICE_UUID],
    local_name_pattern=r"^(Dexcom[A-Z0-9]{2}$|DXCM)",
    description="Dexcom CGM transmitter advertisements",
    version="1.1.0",
    core=False,
)
class DexcomCgmParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        model = None
        serial_tail = None

        advertised = [_normalize_uuid(u) for u in (raw.service_uuids or [])]
        if _G6_NORMALIZED in advertised:
            model = "G6"
        elif _G7_NORMALIZED in advertised:
            model = "G7"

        name = raw.local_name or ""
        m6 = _G6_NAME_RE.match(name)
        if m6:
            model = model or "G6"
            serial_tail = m6.group(1)
        elif _G7_NAME_RE.match(name):
            model = model or "G7"

        if model is None:
            return None

        metadata: dict = {"model": model}
        if raw.local_name:
            metadata["device_name"] = raw.local_name
        if serial_tail:
            metadata["transmitter_serial_tail"] = serial_tail
        if DEVICE_INFO_UUID in (raw.service_uuids or []):
            metadata["has_device_info"] = True

        if serial_tail:
            id_basis = f"dexcom_g6:{serial_tail}"
        else:
            id_basis = raw.mac_address
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="dexcom_cgm",
            beacon_type="dexcom_cgm",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
