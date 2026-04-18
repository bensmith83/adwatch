"""Bosch Professional Toolbox BLE advertisement parser.

Per apk-ble-hunting/reports/bosch-toolbox2_passive.md. Multi-generation tool
family (COMO 1.0 / 1.1 / 2.0) + measuring tools + floodlights. Byte layout
depends on BLE variant discriminator at raw-scan-record byte 7 — we don't
have raw scan record in RawAdvertisement so byte-level decode is deferred.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import _normalize_uuid, register_parser


COMO_1_0_UUID = "02a6c0e0-0451-4000-b000-fb3210111989"
COMO_1_1_2_0_UUID = "fde8"
GCL_UUID = "64588201-6786-4b8a-b98d-23fd72a1c080"
MIRX_UUID = "02a6c0d0-0451-4000-b000-fb3210111989"
COMO2_MEASURING_UUID = "e8fd"  # 0x0000E8FD short form

FLOODLIGHT_HELIOS_UUID  = "30304c0d-511c-4e43-b701-09da37455430"
FLOODLIGHT_EOS_UUID     = "30304c0d-511c-4e43-b702-09da37455430"
FLOODLIGHT_HELIOS2_UUID = "30304c0d-511c-4e43-b703-09da37455430"

_UUID_TO_CATEGORY = {
    _normalize_uuid(COMO_1_0_UUID):       ("power_tool", "COMO_1.0"),
    _normalize_uuid(COMO_1_1_2_0_UUID):   ("power_tool", "COMO_1.1_or_2.0"),
    _normalize_uuid(GCL_UUID):            ("measuring_tool", "GCL"),
    _normalize_uuid(MIRX_UUID):           ("measuring_tool", "MIRX"),
    _normalize_uuid(COMO2_MEASURING_UUID):("measuring_tool", "COMO2"),
    _normalize_uuid(FLOODLIGHT_HELIOS_UUID):  ("floodlight", "Helios"),
    _normalize_uuid(FLOODLIGHT_EOS_UUID):     ("floodlight", "EOS"),
    _normalize_uuid(FLOODLIGHT_HELIOS2_UUID): ("floodlight", "Helios2"),
}


@register_parser(
    name="bosch_toolbox",
    service_uuid=list({
        COMO_1_0_UUID, COMO_1_1_2_0_UUID, GCL_UUID, MIRX_UUID, COMO2_MEASURING_UUID,
        FLOODLIGHT_HELIOS_UUID, FLOODLIGHT_EOS_UUID, FLOODLIGHT_HELIOS2_UUID,
    }),
    description="Bosch Professional tools (COMO / GCL / MIRX / Helios / EOS)",
    version="1.0.0",
    core=False,
)
class BoschToolboxParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        matched_category = None
        matched_family = None
        for u in (raw.service_uuids or []):
            info = _UUID_TO_CATEGORY.get(_normalize_uuid(u))
            if info:
                matched_category, matched_family = info
                break

        if matched_category is None:
            return None

        metadata: dict = {
            "category": matched_category,
            "family": matched_family,
        }
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        payload = raw.manufacturer_payload
        if payload:
            metadata["payload_hex"] = payload.hex()
            metadata["payload_length"] = len(payload)

        id_hash = hashlib.sha256(
            f"bosch:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="bosch_toolbox",
            beacon_type="bosch_toolbox",
            device_class=matched_category,
            identifier_hash=id_hash,
            raw_payload_hex=(payload or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
