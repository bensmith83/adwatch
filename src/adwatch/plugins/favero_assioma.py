"""Favero Assioma power-meter pedal advertisement parser.

Per apk-ble-hunting/reports/favero-assioma_passive.md.

Discovery is purely by SIG company ID **868 / 0x0364** (Favero Electronics
Srl) — `ScanFilter.setManufacturerData(868, null, null)` at `p7/Q.java:44`.
The app reads exactly one byte of the manufacturer payload passively,
`payload[2]`, as a model-variant discriminator (`p7/S.java:150-158`); the
offset is already relative to the bytes *after* the 2-byte company ID, i.e.
`RawAdvertisement.manufacturer_payload[2]` with no shift.

Per-device identity is in the local name: a fixed model prefix
(`ASSIOMA` / `AssiomaPRO` / `A2-` / `A3-` / `A4-`, `q7/EnumC2704b.java:24-44`)
followed by a persistent serial, plus an L/R/U side discriminator
(`p7/S.java:137-148`). That serial survives BLE MAC randomization, so it is
the identity-hash basis.

Power / cadence / balance are **not** passive: they ride the SIG Cycling
Power Measurement characteristic `0x2A63` (notify) after a GATT connect. The
Cycling Power service `0x1818` is vendor-agnostic and is deliberately **not**
registered here.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


# SIG company ID 868 — "Favero Electronics Srl" (_bt_company_ids.py:0x0364).
FAVERO_COMPANY_ID = 0x0364

# Ordered longest/most-specific first; matching is case-sensitive like the app.
MODEL_PREFIXES = (
    ("AssiomaPRO", "PRO"),
    ("ASSIOMA", "legacy"),
    ("A2-", "A2"),
    ("A3-", "A3"),
    ("A4-", "A4"),
)

SIDE_CODES = {
    "L": "left (Duo)",
    "R": "right (Duo)",
    "U": "Uno (single-sided)",
}

# `A2-`/`A3-`/`A4-` alone are too short to be distinctive, so the bare-prefix
# forms require a serial tail.
FAVERO_NAME_PATTERN = r"^(AssiomaPRO|ASSIOMA|A[234]-[0-9A-Za-z]{3,})"
_FAVERO_NAME_RE = re.compile(FAVERO_NAME_PATTERN)


@register_parser(
    name="favero_assioma",
    company_id=FAVERO_COMPANY_ID,
    local_name_pattern=FAVERO_NAME_PATTERN,
    description="Favero Assioma power-meter pedals (Uno / Duo / PRO / A2 / A3 / A4)",
    version="1.0.0",
    core=False,
)
class FaveroAssiomaParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        has_cid = (
            raw.manufacturer_data is not None
            and len(raw.manufacturer_data) >= 2
            and raw.company_id == FAVERO_COMPANY_ID
        )
        name = raw.local_name or ""
        name_hit = bool(_FAVERO_NAME_RE.match(name))

        if not (has_cid or name_hit):
            return None

        metadata: dict = {
            "vendor": "Favero",
            "telemetry": "connect_required_0x2A63",
        }

        payload = raw.manufacturer_payload
        if has_cid:
            metadata["company_id_hex"] = f"0x{FAVERO_COMPANY_ID:04X}"
            if payload and len(payload) > 2:
                variant = payload[2]
                metadata["variant_byte"] = variant
                # The app reads it as a Java signed byte.
                metadata["variant_code"] = variant - 256 if variant >= 128 else variant

        model = serial = None
        if name:
            metadata["device_name"] = name
            for prefix, model_name in MODEL_PREFIXES:
                if name.startswith(prefix):
                    model = model_name
                    metadata["model"] = model_name
                    metadata["model_prefix"] = prefix
                    remainder = name[len(prefix):]
                    if remainder:
                        serial = remainder
                        metadata["serial"] = remainder
                    break

            # Side letter: `S.k` tests the name for a leading L/R/U. Whether it
            # sees the full name or the prefix-stripped remainder is an open
            # question in the report, so check the remainder first, then the
            # whole name.
            for candidate, source in ((serial, "serial"), (name, "device_name")):
                if candidate and candidate[0].upper() in SIDE_CODES:
                    metadata["side"] = SIDE_CODES[candidate[0].upper()]
                    metadata["side_code"] = candidate[0].upper()
                    metadata["side_source"] = source
                    break

        if serial:
            id_basis = f"favero:{model}:{serial}"
        else:
            id_basis = f"favero:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="favero_assioma",
            beacon_type="favero_assioma",
            device_class="fitness_sensor",
            identifier_hash=id_hash,
            raw_payload_hex=(payload or b"").hex() if has_cid else "",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
