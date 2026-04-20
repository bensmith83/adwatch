"""BLE thermal printer parser (cat printer / GOOJPRT / PeriPage).

A huge family of cheap Bluetooth-connected thermal / receipt / label printers
(GB01, GB02, GB03, GT01, MX05, MTP-2, MTP-3, PT-210, PT-220, PeriPage A6,
YT01, GLI1050, etc.) all advertise a common vendor 128-bit service UUID
`e7810a71-73ae-499d-8c15-faa9aef0c3f2` alongside the standard Nordic DFU
UUID `0x18F0`. Only the vendor UUID is distinctive — `18F0` is shared by
every Nordic-DFU-capable device, so we don't register on it. The name
pattern already catches name-only printer ads.

See `docs/protocols/ble-thermal-printer.md` for field layout and references.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


PRINTER_SERVICE_UUID = "e7810a71-73ae-499d-8c15-faa9aef0c3f2"
PRINTER_NAME_PATTERN = (
    r"(?i)^(GB0[123]|GT0[12]|MX0[0-9]|PT-?2[01]0|MTP-?[23]|PeriPage[\w\-]*|YT01|GLI\d{3,4})"
)
_MODEL_RE = re.compile(PRINTER_NAME_PATTERN)


@register_parser(
    name="thermal_printer",
    service_uuid=PRINTER_SERVICE_UUID,
    local_name_pattern=PRINTER_NAME_PATTERN,
    description="BLE thermal / receipt / label printer (cat printer, GOOJPRT, PeriPage, GLI)",
    version="1.0.0",
    core=False,
)
class ThermalPrinterParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        name = raw.local_name or ""
        uuids = [u.lower() for u in (raw.service_uuids or [])]

        has_vendor_uuid = PRINTER_SERVICE_UUID in uuids
        name_match = _MODEL_RE.match(name) if name else None

        if not has_vendor_uuid and not name_match:
            return None

        metadata: dict = {}
        if name:
            metadata["device_name"] = name
        if name_match:
            metadata["model"] = name_match.group(1).upper().replace("-", "")
        if has_vendor_uuid:
            metadata["vendor_uuid"] = PRINTER_SERVICE_UUID

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:thermal_printer".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="thermal_printer",
            beacon_type="thermal_printer",
            device_class="printer",
            identifier_hash=id_hash,
            raw_payload_hex=raw.manufacturer_data.hex() if raw.manufacturer_data else "",
            metadata=metadata,
        )
