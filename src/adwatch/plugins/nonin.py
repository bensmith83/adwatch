"""Nonin Medical BLE pulse oximeter plugin (3150 / 3230).

Per apk-ble-hunting/reports/medixine-nonin-devicehub_passive.md.

The Medixine Device Hub companion app is a MAC-provisioned hub: it scans by
saved device address only and decodes **no** manufacturer data, service data or
name. So the passive discriminators come from the device itself:

  - Nonin proprietary oximeter service `46A970E0-0D5F-11E2-8B5E-0002A5D5C51B`
    (the tail `0002A5D5C51B` is Nonin's Bluetooth OUI).
  - Model name `Nonin_3150` / `Nonin_3230` (display-label strings in the app;
    the digits are the model number).

The SIG Pulse Oximeter Service `0x1822` is vendor-agnostic, so it is recorded
as an enrichment when a Nonin signal is already present but is never a match
criterion on its own.

No SpO2/pulse telemetry is broadcast — measurements are connected-GATT only
(`2A5F` on the 3150, vendor notify chars on both). The app relies on a static
MAC for reconnection, so the MAC is the stable identity basis here.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


NONIN_SERVICE_UUID = "46a970e0-0d5f-11e2-8b5e-0002a5d5c51b"
SIG_PLX_SERVICE_UUID = "1822"  # vendor-agnostic — never matched alone

NONIN_MODELS = {
    "3150": "WristOx2 3150",
    "3230": "Nonin Connect 3230",
}

# Exported so other medical plugins can stand down on a bare SIG-UUID hit
# (see plugins/omron.py) rather than double-claiming a Nonin oximeter.
NONIN_NAME_PATTERN = r"^nonin[ _-]?(\d{3,4})\b"

_NONIN_NAME_RE = re.compile(NONIN_NAME_PATTERN, re.IGNORECASE)


def _uuids(raw: RawAdvertisement) -> set[str]:
    found = {u.lower() for u in (raw.service_uuids or [])}
    found |= {k.lower() for k in (raw.service_data or {})}
    return found


@register_parser(
    name="nonin",
    service_uuid=NONIN_SERVICE_UUID,
    local_name_pattern=r"(?i)^nonin[ _-]?\d{3,4}",
    description="Nonin Medical pulse oximeter (3150 / 3230)",
    version="1.0.0",
    core=False,
)
class NoninParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        advertised = _uuids(raw)
        uuid_hit = NONIN_SERVICE_UUID in advertised
        name = raw.local_name or ""
        name_match = _NONIN_NAME_RE.match(name)

        if not (uuid_hit or name_match):
            return None

        metadata: dict = {"vendor": "Nonin Medical"}
        if uuid_hit:
            metadata["nonin_service"] = True
        if name:
            metadata["device_name"] = name
        if name_match:
            model = name_match.group(1)
            metadata["model"] = model
            friendly = NONIN_MODELS.get(model)
            if friendly:
                metadata["model_name"] = friendly
        # SIG Pulse Oximeter Service — corroborates device type, never matched
        # on its own (any vendor's oximeter may advertise it).
        if SIG_PLX_SERVICE_UUID in advertised or any(
            u.startswith("00001822-") for u in advertised
        ):
            metadata["plx_service_advertised"] = True

        # Pre-provisioned MAC model: the backend hands the app a static address,
        # so the MAC is the stable identifier for this device family.
        id_hash = hashlib.sha256(f"nonin:{raw.mac_address}".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="nonin",
            beacon_type="nonin",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )
