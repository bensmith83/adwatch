"""Anova appliance BLE advertisement parser (Precision Cooker / Precision Oven).

Detection by service UUIDs or the ``Anova`` name prefix -- no byte-level
telemetry is broadcast.

Sous-vide circulator UUIDs come from
`apk-ble-hunting/reports/anovaculinary-android_passive.md`.

`anovaculinary-anovaoven_passive.md` (Precision Oven) is a Hermes/React
Native build: its service UUIDs, manufacturer data and advertised-name
pattern all live in HBC bytecode and are **not** statically recoverable.
The only usable artifact from that report is the product-name vocabulary
("Anova Precision Oven", "... Oven 1", "... Oven 2"), so an oven that
advertises a name in that family is matched by the existing ``^Anova``
regex and classified here. Nothing in that report justified a new UUID or
a speculative ``APO-*`` name regex.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


ANOVA_UUID_LEGACY = "ffe0"
ANOVA_UUID_NEURON = "0e140000-0af1-4582-a242-773e63054c68"
ANOVA_UUID_SDK = "09fa0000-216b-488b-a937-d6ebca664b24"

ANOVA_NAME_PATTERN = r"(?i)^Anova"

PRODUCT_LINE_OVEN = "precision_oven"
PRODUCT_LINE_SOUS_VIDE = "sous_vide_circulator"

# Applied only to names that already matched the Anova prefix, so these are
# refinements rather than additional match criteria.
_PRODUCT_LINES = [
    (re.compile(r"(?i)precision\s+oven"), PRODUCT_LINE_OVEN, "Anova Precision Oven", "oven"),
    (re.compile(r"(?i)(precision\s+cooker|nano)"), PRODUCT_LINE_SOUS_VIDE,
     "Anova Precision Cooker", "appliance"),
]


@register_parser(
    name="anova",
    service_uuid=[ANOVA_UUID_NEURON, ANOVA_UUID_SDK],
    local_name_pattern=ANOVA_NAME_PATTERN,
    description="Anova Precision Cooker sous-vide / Precision Oven",
    version="1.1.0",
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

        metadata: dict = {"vendor": "Anova"}
        device_class = "appliance"
        if name:
            metadata["device_name"] = name
        if has_anova_uuid:
            metadata["has_anova_service"] = True

        if has_anova_name:
            for pattern, product_line, model, klass in _PRODUCT_LINES:
                if pattern.search(name):
                    metadata["product_line"] = product_line
                    metadata["model"] = model
                    device_class = klass
                    break

        id_hash = hashlib.sha256(f"anova:{raw.mac_address}".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="anova",
            beacon_type="anova",
            device_class=device_class,
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )
