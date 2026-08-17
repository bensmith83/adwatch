"""Aktiia / Hilo cuffless optical blood-pressure bracelet plugin.

Per apk-ble-hunting/reports/aktiia-android-production_passive.md the app itself
supplies **no** advertisement fingerprint: it scans unfiltered, captures the
advertising name for backend verification only, and thereafter addresses the
device by MAC. There is no company ID, no service-data parsing, no name prefix
and no byte layout to decode — nothing physiological is broadcast.

The one reusable signal the report recommends is the vendor's own 128-bit UUID
family (all plain-text literals in `com.aktiia.ble`), so this plugin is a
presence-only detector for those:

  ``3A350001-E7CC-4D7F-9683-ED4CB1001CD1``  Pod token-authorization service
  ``A6B41001-…`` / ``A6B41010-…``           Pod raw-data / HBS services
  ``A6B40001-…``                            Cuff measurement (A6B400xx family)
  ``B1E71568-047B-47C4-88C9-0F90E397ACF7``  Cuff measurement service

Caveat, stated plainly: these are the *GATT* services. The app builds a
``setServiceUuid`` filter from them and then discards it, so whether the
firmware actually advertises any of them is unverified — confirm against a live
capture. They are vendor-unique, so a false positive is not a realistic risk.

The registry matches UUIDs exactly, so only the known members are registered;
``parse()`` additionally accepts any suffix on the ``…-003d-4e65-9208-08f4db958863``
vendor base. Identity falls back to the MAC (the app relies on a stable address
for bonding, and no in-payload identifier exists).
"""

import hashlib
import re

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import _normalize_uuid, register_parser


POD_TOKEN_AUTH_UUID = "3a350001-e7cc-4d7f-9683-ed4cb1001cd1"
POD_RAW_DATA_UUID = "a6b41001-003d-4e65-9208-08f4db958863"
POD_HBS_UUID = "a6b41010-003d-4e65-9208-08f4db958863"
CUFF_A6B4_UUID = "a6b40001-003d-4e65-9208-08f4db958863"
CUFF_MEASUREMENT_UUID = "b1e71568-047b-47c4-88c9-0f90e397acf7"

AKTIIA_SERVICE_UUIDS = (
    POD_TOKEN_AUTH_UUID,
    POD_RAW_DATA_UUID,
    POD_HBS_UUID,
    CUFF_A6B4_UUID,
    CUFF_MEASUREMENT_UUID,
)

# A6B4 1xxx = Pod, A6B4 0xxx = Cuff, on the shared vendor base.
_VENDOR_BASE_RE = re.compile(r"^a6b4([01])[0-9a-f]{3}-003d-4e65-9208-08f4db958863$")

_PERIPHERAL_BY_UUID = {
    _normalize_uuid(POD_TOKEN_AUTH_UUID): "pod",
    _normalize_uuid(CUFF_MEASUREMENT_UUID): "cuff",
}


@register_parser(
    name="aktiia",
    service_uuid=AKTIIA_SERVICE_UUIDS,
    description="Aktiia / Hilo cuffless blood-pressure bracelet and reference cuff",
    version="1.0.0",
    core=False,
)
class AktiiaParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        candidates = [u.lower() for u in (raw.service_uuids or [])]
        candidates += [k.lower() for k in (raw.service_data or {})]

        matched = None
        peripheral = None
        for uuid in candidates:
            normalized = _normalize_uuid(uuid)
            if normalized in _PERIPHERAL_BY_UUID:
                matched, peripheral = uuid, _PERIPHERAL_BY_UUID[normalized]
                break
            base = _VENDOR_BASE_RE.match(normalized)
            if base:
                matched = uuid
                peripheral = "pod" if base.group(1) == "1" else "cuff"
                break

        if matched is None:
            return None

        metadata: dict = {
            "vendor": "Aktiia / Hilo",
            "product": "cuffless optical blood-pressure monitor",
            "peripheral": peripheral,
            "matched_service": matched,
        }
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        id_hash = hashlib.sha256(f"aktiia:{raw.mac_address}".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="aktiia",
            beacon_type="aktiia",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
