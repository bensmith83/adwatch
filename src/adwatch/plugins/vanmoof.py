"""VanMoof e-bike advertisement parser.

Per apk-ble-hunting/reports/vanmoof-app_passive.md.

The app itself is R8-flattened into ``defpackage.*`` so the scan-filter chain
is not directly recoverable, but Stage 4 pulled 157 UUIDs out of the dex and
two shapes are usable passively:

* the vendor-squatted 16-bit UUID ``0x8A0E`` used by the modern Electrified
  line, and
* per-generation 128-bit family UUIDs (``…5500-…``) for the older bikes.

The frame number — the 5-character serial stamped on the bike — is broadcast
inside the local name (``VANMOOF-S3-XXXXX`` / ``VanMoof BL-XXXXX``). That
claim comes from public RE work (vanbike-lib), not from the APK, so the name
regex is treated as enrichment on top of the UUID match, and the parser still
reports a bike when only the name matches.

``F000FFC0-…`` (TI OAD) marks a bike in firmware-update mode, but it is a
generic TI bootloader UUID shared by every CC254x product, so it is only read
as a flag *alongside* a VanMoof signal — never as a match on its own.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import _normalize_uuid, register_parser


VANMOOF_SHORT_UUID = "8a0e"

# 128-bit per-generation family UUIDs -> bike generation.
VANMOOF_FAMILY_UUIDS = {
    "278d5500-4692-039f-3445-a23fc55333d0": "SmartBike",
    "6acb5500-e631-4069-944d-b8ca7598ad50": "Electrified S2/X2",
    "6acc5500-e631-4069-944d-b8ca7598ad50": "Electrified S3/X3",
}

VANMOOF_SERVICE_UUIDS = [VANMOOF_SHORT_UUID, *VANMOOF_FAMILY_UUIDS]

# SIG company ID for "VANMOOF Global Holding B.V." (_bt_company_ids.py:0x0A4F).
# No mfr-data was observed statically; registered so a live-capture payload is
# still routed here.
VANMOOF_COMPANY_ID = 0x0A4F

TI_OAD_UUID = "f000ffc0-0451-4000-b000-000000000000"

VANMOOF_NAME_PATTERN = r"^(?i:vanmoof)\b"
_ELECTRIFIED_NAME_RE = re.compile(r"^VANMOOF[- ]([A-Z0-9]{1,3})[- ]([A-Z0-9]{4,6})$", re.I)
_SMARTBIKE_NAME_RE = re.compile(r"^VanMoof[- ]BL[- ]([A-Z0-9]{4,6})$", re.I)

_NORMALIZED_FAMILY = {_normalize_uuid(u): g for u, g in VANMOOF_FAMILY_UUIDS.items()}
_NORMALIZED_SHORT = _normalize_uuid(VANMOOF_SHORT_UUID)
_NORMALIZED_TI_OAD = _normalize_uuid(TI_OAD_UUID)


@register_parser(
    name="vanmoof",
    company_id=VANMOOF_COMPANY_ID,
    service_uuid=VANMOOF_SERVICE_UUIDS,
    local_name_pattern=VANMOOF_NAME_PATTERN,
    description="VanMoof e-bikes (SmartBike / Electrified S-X series)",
    version="1.0.0",
    core=False,
)
class VanMoofParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        advertised = [_normalize_uuid(u) for u in (raw.service_uuids or [])]

        generation = None
        for uuid in advertised:
            if uuid in _NORMALIZED_FAMILY:
                generation = _NORMALIZED_FAMILY[uuid]
                break
        if generation is None and _NORMALIZED_SHORT in advertised:
            generation = "Electrified (modern)"

        name = raw.local_name or ""
        name_hit = bool(re.match(VANMOOF_NAME_PATTERN, name))
        has_cid = (
            raw.manufacturer_data is not None
            and len(raw.manufacturer_data) >= 2
            and raw.company_id == VANMOOF_COMPANY_ID
        )

        if not (generation or name_hit or has_cid):
            return None

        metadata: dict = {"vendor": "VanMoof"}
        if generation:
            metadata["generation"] = generation
        if has_cid:
            metadata["company_id_hex"] = f"0x{VANMOOF_COMPANY_ID:04X}"
            if raw.manufacturer_payload:
                metadata["manufacturer_payload_hex"] = raw.manufacturer_payload.hex()

        frame_number = None
        if name:
            metadata["device_name"] = name
            m = _SMARTBIKE_NAME_RE.match(name)
            if m:
                frame_number = m.group(1)
                metadata["model"] = "SmartBike"
            else:
                m = _ELECTRIFIED_NAME_RE.match(name)
                if m:
                    metadata["model"] = m.group(1).upper()
                    frame_number = m.group(2)
            if frame_number:
                metadata["frame_number"] = frame_number

        if _NORMALIZED_TI_OAD in advertised:
            metadata["dfu_mode"] = True

        if frame_number:
            id_basis = f"vanmoof:{frame_number}"
        else:
            id_basis = f"vanmoof:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="vanmoof",
            beacon_type="vanmoof",
            device_class="vehicle",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
