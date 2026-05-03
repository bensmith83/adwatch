"""Honeywell / Resideo Lyric thermostat onboarding plugin.

Per apk-ble-hunting/reports/honeywell-android-lyric_passive.md: Lyric
T-series thermostats and Resideo water-leak detectors are Wi-Fi-primary
devices that broadcast over BLE only during commissioning. Discovery is
by exact name prefix ``HON_NP`` (Honeywell Network-Provisioning) plus an
optional service UUID.

Presence of this beacon strongly implies the device is in unprovisioned
state — useful as a "new device just arrived at this address" signal.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


LYRIC_SERVICE_UUID = "8821813e-71eb-43e2-9a82-9ce3dc4ed266"

_NAME_RE = re.compile(r"^HON_NP(?:[_-](.+))?$")


@register_parser(
    name="honeywell_lyric",
    service_uuid=LYRIC_SERVICE_UUID,
    local_name_pattern=r"^HON_NP",
    description="Honeywell Lyric / Resideo onboarding beacon",
    version="1.0.0",
    core=False,
)
class HoneywellLyricParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        uuid_hit = LYRIC_SERVICE_UUID in normalized

        local_name = raw.local_name or ""
        name_match = _NAME_RE.match(local_name)

        if not (uuid_hit or name_match):
            return None

        metadata: dict = {
            "vendor": "Honeywell/Resideo",
            "unprovisioned": True,
        }
        suffix: str | None = None
        if name_match:
            metadata["device_name"] = local_name
            if name_match.group(1):
                suffix = name_match.group(1)
                metadata["serial_suffix"] = suffix

        if suffix:
            id_basis = f"honeywell_lyric:{suffix}"
        else:
            id_basis = f"honeywell_lyric:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="honeywell_lyric",
            beacon_type="honeywell_lyric",
            device_class="thermostat",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
