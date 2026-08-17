"""NeuroMetrix Quell TENS (wearable pain-relief) plugin.

Per apk-ble-hunting/reports/neurometrix-quell_passive.md.

Quell is a connect-to-control device, not a telemetry beacon. Its
``ScanRecordParser`` walks GAP AD structures and selects devices by the presence
of the Quell **128-bit vendor service UUID** in the 0x06/0x07 UUID list. It also
reads the 0xFF manufacturer block, extracting only the 2-byte little-endian
company ID and storing the remainder **raw** — the app never decodes a single
field, so no byte layout is asserted here.

Anchor caveat: the report pins the vendor base
``75000d1f-XXXX-40f7-8204-ee627068ec88`` but not the 16-bit anchor
(``BluetoothCommon`` failed to decompile); ``0x1000`` is the stated likely
value. The registry only does exact UUID matching, so ``…-1000-…`` is
registered, while :meth:`parse` accepts **any** anchor on that base — the
128-bit base itself is the vendor-unique signal. A device on a different anchor
will only reach this parser via the (unverified) name pattern; that is recorded
as ``confidence: low``.

Nothing therapy-related (battery, intensity, program) is broadcast. The
``SerialNumberAnnotator`` byte-rotation decode is a connected-session concern
and is deliberately not applied to advertisement bytes.

Privacy: the product-specific vendor UUID lets a passive observer infer a
chronic-pain TENS user. Flagged ``sensitive=True``.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


# Likely anchor (0x1000) on the Quell vendor base — registered for exact match.
QUELL_SERVICE_UUID = "75000d1f-1000-40f7-8204-ee627068ec88"
# Any anchor on the vendor base is accepted inside parse().
_QUELL_BASE_RE = re.compile(
    r"^75000d1f-([0-9a-f]{4})-40f7-8204-ee627068ec88$", re.I
)
# Unverified in the decompile (the app filters by UUID, not name) — kept as a
# low-confidence fallback so units on an unexpected anchor are still seen.
QUELL_NAME_PATTERN = r"(?i)^Quell\b"


@register_parser(
    name="quell",
    service_uuid=QUELL_SERVICE_UUID,
    local_name_pattern=QUELL_NAME_PATTERN,
    description="NeuroMetrix Quell wearable TENS (presence-only)",
    version="1.0.0",
    core=False,
)
class QuellParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        anchor = None
        for advertised in (raw.service_uuids or []):
            m = _QUELL_BASE_RE.match(advertised)
            if m:
                anchor = m.group(1).lower()
                break

        local_name = raw.local_name or ""
        name_hit = bool(re.match(QUELL_NAME_PATTERN, local_name))

        if anchor is None and not name_hit:
            return None

        metadata: dict = {
            "vendor": "NeuroMetrix",
            "product": "Quell TENS",
            "match_basis": "service_uuid" if anchor else "local_name",
            "confidence": "high" if anchor else "low",
            "telemetry": "none (connect-only GATT)",
            "sensitive": True,
            "sensitive_category": "chronic_pain_therapy",
        }
        if anchor is not None:
            metadata["service_uuid_anchor"] = anchor
        if local_name:
            metadata["device_name"] = local_name

        # The app reads the company ID but stores the payload raw and decodes
        # nothing; surface both without inventing a layout.
        if raw.company_id is not None:
            metadata["company_id"] = raw.company_id
            payload = raw.manufacturer_payload or b""
            metadata["mfr_payload_hex"] = payload.hex()
            metadata["mfr_payload_len"] = len(payload)
            metadata["mfr_payload_decoded"] = False

        # No confirmed per-unit identifier is broadcast (the serial is a
        # connected-session read), so the MAC is the only anchor.
        id_hash = hashlib.sha256(
            f"quell:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="quell",
            beacon_type="quell",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
