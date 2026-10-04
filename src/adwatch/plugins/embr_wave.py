"""Embr Wave 2 thermoregulation wristband plugin.

Per apk-ble-hunting/reports/embrlabs-eden_passive.md: react-native-ble-plx
scans on the advertised vendor service UUID
``00002001-1112-EFDE-1523-725A2AAB0123``. No manufacturer/service data or
in-advert serial was recovered, so this is presence-only with MAC identity.

DFU mode advertises the generic Nordic DFU service 0xFE59 instead; that is a
shared signal and is deliberately NOT registered here.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser, _normalize_uuid


EMBR_SERVICE_UUID = "00002001-1112-efde-1523-725a2aab0123"


@register_parser(
    name="embr_wave",
    service_uuid=EMBR_SERVICE_UUID,
    description="Embr Wave 2 thermoregulation wristband (presence-only)",
    version="1.0.0",
    core=False,
)
class EmbrWaveParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        uuids = {_normalize_uuid(u) for u in (raw.service_uuids or [])}
        if EMBR_SERVICE_UUID not in uuids:
            return None

        metadata: dict = {
            "vendor": "Embr Labs",
            "product": "Embr Wave 2",
            "mode": "app",
            "telemetry": "none (post-connect GATT only)",
            # Hot-flash relief is a common use case (menopause inference).
            "sensitive": True,
            "sensitive_category": "reproductive_health",
        }
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        id_hash = hashlib.sha256(f"embrwave:{raw.mac_address}".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="embr_wave",
            beacon_type="embr_wave",
            device_class="wearable",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
