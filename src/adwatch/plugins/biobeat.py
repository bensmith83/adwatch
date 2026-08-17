"""Biobeat BB-613WP cuffless BP / SpO2 monitor plugin.

Per apk-ble-hunting/reports/biobeat-abpm_passive.md (`cloud.biobeat.abpm`,
scanner in `z2/C1389E.java`):

  - Discovery is a single ``ScanFilter`` on the **advertised** 128-bit service
    UUID ``3FD4750B-CFF6-405C-AF2C-BC0E76193183`` (`C1389E.java:49,169`). This
    is *not* the GATT service the characteristics live under
    (``2905B9AA-6B1F-4C49-9C26-9BFC88350290``, `h2/I.java:81,84`), which is
    matched here only as a secondary signal.
  - A result is kept only when ``device.getName()`` is non-null and non-empty
    (`C1389E.java:88,145`); there is **no** name prefix — do not assume
    ``BB-``/``BioBeat``. That gate is reported as ``app_discoverable``.
  - No manufacturer-data or service-data parsing exists anywhere in the app, so
    the advertisement carries presence only. BP/SpO2/PPG, serial and firmware
    are GATT reads behind the echo-challenge auth.
  - The firmware has an iBeacon-enable characteristic (``4B965E9F-…``), so a
    unit may *additionally* emit Apple iBeacon frames; those are handled by the
    core ibeacon parser, not here.

Identity therefore falls back to the MAC (reconnect is MAC-based, so a static
address is likely).
"""

import hashlib

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import _normalize_uuid, register_parser


BIOBEAT_ADVERTISED_SERVICE_UUID = "3fd4750b-cff6-405c-af2c-bc0e76193183"
BIOBEAT_GATT_SERVICE_UUID = "2905b9aa-6b1f-4c49-9c26-9bfc88350290"

_ADVERTISED_NORMALIZED = _normalize_uuid(BIOBEAT_ADVERTISED_SERVICE_UUID)
_GATT_NORMALIZED = _normalize_uuid(BIOBEAT_GATT_SERVICE_UUID)


@register_parser(
    name="biobeat",
    service_uuid=(BIOBEAT_ADVERTISED_SERVICE_UUID, BIOBEAT_GATT_SERVICE_UUID),
    description="Biobeat BB-613WP cuffless blood-pressure / SpO2 monitor",
    version="1.0.0",
    core=False,
)
class BiobeatParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        advertised = {_normalize_uuid(u) for u in (raw.service_uuids or [])}
        advertised |= {_normalize_uuid(k) for k in (raw.service_data or {})}

        if _ADVERTISED_NORMALIZED in advertised:
            matched = "advertised"
        elif _GATT_NORMALIZED in advertised:
            matched = "gatt"
        else:
            return None

        metadata: dict = {
            "vendor": "Biobeat",
            "model": "BB-613WP cuffless BP/SpO2 monitor",
            "matched_service": matched,
            "app_discoverable": bool(raw.local_name),
        }
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        id_hash = hashlib.sha256(f"biobeat:{raw.mac_address}".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="biobeat",
            beacon_type="biobeat",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
