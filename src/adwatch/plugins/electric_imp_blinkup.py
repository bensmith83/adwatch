"""Electric Imp (Twilio) BlinkUp BLE provisioning plugin.

Per apk-ble-hunting/reports/tovala-tovala_passive.md: the Tovala smart oven
commissions Wi-Fi over "bleblinkup", Electric Imp's BLE flavour of BlinkUp.
The app's constants module holds a single vendor service UUID as a
``ParcelUuid`` for scan filtering (`rq/e.java:56`) --

    FADA47BE-C455-48C9-A5F2-AF7CF368D719

-- with 9 vendor characteristics (Wi-Fi config, scan list, status, MAC,
control) plus SIG Device Information behind it. Nothing else is passively
visible: the app parses no manufacturer data and no service data, and the
advertised-name convention is not recoverable (the BlinkUp wrapper is
R8-renamed and the native libs were absent from the base APK).

Scope note: this UUID identifies the **BlinkUp module**, not Tovala. The
same Electric Imp module ships across many vendors, so a Tovala claim is
only attached when the advertised name says so. Because BlinkUp BLE is a
commissioning channel, a hit means the device is unprovisioned or in setup
mode -- the same lifecycle signal as `improv_wifi` / `espressif_prov`.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


BLINKUP_SERVICE_UUID = "fada47be-c455-48c9-a5f2-af7cf368d719"

# Electric Imp's stock advertised names per the public BlinkUp docs. Used as
# an enrichment flag only -- too weak to match on by itself.
_IMP_DEFAULT_NAME_RE = re.compile(r"(?i)^imp[-_]")
_TOVALA_NAME_RE = re.compile(r"(?i)tovala")


@register_parser(
    name="electric_imp_blinkup",
    service_uuid=BLINKUP_SERVICE_UUID,
    description="Electric Imp BlinkUp BLE Wi-Fi provisioning (e.g. Tovala oven)",
    version="1.0.0",
    core=False,
)
class ElectricImpBlinkUpParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        service_data = raw.service_data or {}
        blob = None
        for key, value in service_data.items():
            if key.lower() == BLINKUP_SERVICE_UUID:
                blob = value
                break

        if BLINKUP_SERVICE_UUID not in normalized and blob is None:
            return None

        metadata: dict = {
            "ecosystem": "electric-imp-blinkup",
            "provisioning_mode": True,
            "transport": "ble_blinkup",
        }

        name = raw.local_name or ""
        if name:
            metadata["device_name"] = name
            if _IMP_DEFAULT_NAME_RE.match(name):
                metadata["imp_default_name"] = True
            if _TOVALA_NAME_RE.search(name):
                metadata["product_hint"] = "Tovala Smart Oven"

        if blob is not None:
            metadata["service_data_hex"] = blob.hex()

        id_basis = f"electric_imp_blinkup:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="electric_imp_blinkup",
            beacon_type="electric_imp_blinkup",
            device_class="provisioning",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
