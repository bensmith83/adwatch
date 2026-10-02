"""Roche CoaguChek INRange / Vantus home INR meter plugin.

Per apk-ble-hunting/reports/biotelemetry-remoteinr_passive.md: the Remote INR
app scans unfiltered and accepts a device solely by MAC OUI ``B8:78:79`` (plus
a non-null advertised name, whose content is not inspected). Nothing is
broadcast beyond identity; INR results move only post-bond over GATT.

Presence implies anticoagulation therapy, so results are flagged sensitive.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


COAGUCHEK_OUI = "B8:78:79"


@register_parser(
    name="coaguchek",
    mac_prefix=COAGUCHEK_OUI,
    description="Roche CoaguChek INRange/Vantus INR meter (presence-only, MAC OUI)",
    version="1.0.0",
    core=False,
)
class CoaguChekParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.mac_address.upper().startswith(COAGUCHEK_OUI):
            return None

        metadata: dict = {
            "vendor": "Roche",
            "product": "CoaguChek INRange / Vantus INR meter",
            "match_basis": "mac_oui",
            "name_present": bool(raw.local_name),
            "telemetry": "none (post-bond GATT only)",
            "sensitive": True,
            "sensitive_category": "anticoagulation_therapy",
        }
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        id_hash = hashlib.sha256(f"coaguchek:{raw.mac_address}".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="coaguchek",
            beacon_type="coaguchek",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
