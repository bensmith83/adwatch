"""Ayla Networks BLE Wi-Fi-setup beacon plugin.

Per apk-ble-hunting/reports/owletcare-sleep_passive.md. The Owlet Dream Sock
base station uses the Ayla Networks BLE setup SDK for Wi-Fi onboarding, and
the *only* thing a passive scanner sees is the SIG-assigned Ayla Networks
16-bit service UUID ``0xFE28`` (``AylaGenericGattService.SERVICE_UUID``),
optionally alongside the Ayla Wi-Fi-config service
``1CF0FE66-3ECF-4D6E-A9FC-E287AB124B96``.

The UUID belongs to the Ayla *platform*, not to any one brand — Owlet is one
of many Ayla-powered IoT vendors — so this parser deliberately reports
"Ayla Networks provisioning" rather than attributing the device to Owlet.
(``owlet.py`` keeps the Owlet-specific CID 0x0E9F / vendor UUID match.)

No manufacturer data, no service data, no telemetry and no persistent
identifier are broadcast: the DSN/serial is a connection-gated GATT read.
A hit means "an Ayla-platform device is in Wi-Fi-setup mode nearby".
"""

import hashlib

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import _normalize_uuid, register_parser


# SIG-assigned 16-bit UUID for Ayla Networks (AylaGenericGattService).
AYLA_SERVICE_UUID = "0000fe28-0000-1000-8000-00805f9b34fb"
# AylaWiFiConfigGattService — the credential-transfer service.
AYLA_WIFI_CONFIG_UUID = "1cf0fe66-3ecf-4d6e-a9fc-e287ab124b96"

_AYLA_NORM = _normalize_uuid(AYLA_SERVICE_UUID)
_WIFI_CFG_NORM = _normalize_uuid(AYLA_WIFI_CONFIG_UUID)


@register_parser(
    name="ayla_prov",
    service_uuid=[AYLA_SERVICE_UUID, AYLA_WIFI_CONFIG_UUID],
    description="Ayla Networks BLE Wi-Fi setup beacon (Owlet base station et al.)",
    version="1.0.0",
    core=False,
)
class AylaProvParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        advertised = {_normalize_uuid(u) for u in (raw.service_uuids or [])}
        has_identity = _AYLA_NORM in advertised
        has_wifi_config = _WIFI_CFG_NORM in advertised

        if not (has_identity or has_wifi_config):
            return None

        metadata: dict = {
            "vendor": "Ayla Networks",
            "setup_mode": True,
            "has_identity_service": has_identity,
            "has_wifi_config_service": has_wifi_config,
        }
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        id_hash = hashlib.sha256(
            f"ayla_prov:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="ayla_prov",
            beacon_type="ayla_prov",
            device_class="provisioning",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
