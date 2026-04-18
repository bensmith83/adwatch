"""Anova Precision Cooker BLE advertisement parser.

Per apk-ble-hunting/reports/anovaculinary-android_passive.md. Detection by
service UUIDs only — no byte-level telemetry in the advertisement.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


ANOVA_UUID_LEGACY = "ffe0"
ANOVA_UUID_NEURON = "0e140000-0af1-4582-a242-773e63054c68"
ANOVA_UUID_SDK = "09fa0000-216b-488b-a937-d6ebca664b24"


@register_parser(
    name="anova",
    service_uuid=[ANOVA_UUID_NEURON, ANOVA_UUID_SDK],
    local_name_pattern=r"(?i)^Anova",
    description="Anova Precision Cooker sous-vide",
    version="1.0.0",
    core=False,
)
class AnovaParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        name = raw.local_name or ""
        has_anova_name = name.lower().startswith("anova")
        has_anova_uuid = any(
            u.lower() in (ANOVA_UUID_NEURON, ANOVA_UUID_SDK)
            for u in (raw.service_uuids or [])
        )

        if not (has_anova_name or has_anova_uuid):
            return None

        metadata: dict = {}
        if name:
            metadata["device_name"] = name
        if has_anova_uuid:
            metadata["has_anova_service"] = True

        id_hash = hashlib.sha256(f"anova:{raw.mac_address}".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="anova",
            beacon_type="anova",
            device_class="appliance",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )
