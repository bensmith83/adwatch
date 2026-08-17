"""Aluna smart-spirometer BLE plugin.

Per apk-ble-hunting/reports/aluna-app_passive.md (app ``com.aluna.app``).

A clean service-UUID-only target: the app's single ``ScanFilter`` matches the
128-bit spirometry service ``AAF0D58C-8DDB-4BEB-AD66-41AE54FCB3D1`` and reads
nothing else out of the advertisement — no manufacturer data, no service data,
no name filter.  All telemetry (battery, flow, pressure, firmware, device ID)
lives behind a connected GATT session, so presence and RSSI proximity are the
only passive signals.

Aluna also holds SIG company ID ``0x06E4``.  The report does not confirm the
device emits manufacturer data, but the ID is Aluna's own registration, so it
is accepted as a secondary match and its payload is recorded as hex only —
the layout is undocumented and must come from a live capture.

Detecting this advertisement identifies a respiratory-health medical device,
which is sensitive to associate with a person or place.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

ALUNA_SERVICE_UUID = "aaf0d58c-8ddb-4beb-ad66-41ae54fcb3d1"
ALUNA_COMPANY_ID = 0x06E4


@register_parser(
    name="aluna",
    company_id=ALUNA_COMPANY_ID,
    service_uuid=ALUNA_SERVICE_UUID,
    description="Aluna smart spirometer advertisements",
    version="1.0.0",
    core=False,
)
class AlunaParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        uuid_hit = ALUNA_SERVICE_UUID in {u.lower() for u in (raw.service_uuids or [])}
        cid_hit = raw.company_id == ALUNA_COMPANY_ID

        if not (uuid_hit or cid_hit):
            return None

        metadata: dict = {
            "vendor": "Aluna",
            "product": "smart spirometer",
            "match_source": "service_uuid" if uuid_hit else "company_id",
        }
        if raw.local_name:
            metadata["device_name"] = raw.local_name
        if cid_hit and raw.manufacturer_payload:
            # Layout undocumented — surface the bytes without interpreting them.
            metadata["payload_hex"] = raw.manufacturer_payload.hex()

        # Nothing identifying is advertised, so the MAC is all there is.
        id_hash = hashlib.sha256(f"aluna:{raw.mac_address}".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="aluna",
            beacon_type="aluna",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
