"""Eko digital stethoscope (CORE / DUO family) advertisement parser.

Per apk-ble-hunting/reports/ekodevices-android_passive.md.

Discovery is a pure service-UUID filter — `scanForPeripheralsWithServices`
over the nine UUIDs in `EDLibCore.getAdvertisedServices()` — with the local
name used only to disambiguate the two legacy models that share the
`5BF6E500-…` data service (`EDBLEDeviceType.from(...)`,
`EDBLEConstants.java:64-67`). The app parses **no** manufacturer data and
**no** service data, and the advert carries no serial or telemetry: battery,
recording state and the audio/ECG streams are all post-connect GATT.

The one operational signal that does leak is firmware-update mode — either a
DFU-specific service UUID or a `DFU` / `required` marker in the local name
(`EDPeripheral.java:146-148`).
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import _normalize_uuid, register_parser


LEGACY_SHARED_UUID = "5bf6e500-9999-11e3-a116-0002a5d5c51b"
CORE2_UUID = "f1de0ef3-6e8f-4fa6-b538-5bd318bdbccb"
NORDIC_DFU_UUID = "00060000-f8ce-11e4-abf4-0002a5d5c51b"
DUO15_UUID = "128c9930-5ad6-41fd-be20-19be7e82602e"
DUO15_DFU_UUID = "7bb44072-14f7-42c2-b0de-2a340909b180"
DUO3_UUID = "c2de8abd-959b-4f00-bd84-556a0f45ee28"
DUO3_DFU_UUID = "b532b98b-7d69-4cdb-b7d0-297a77478790"
CORE2_DFU_UUID = "c2d4f30f-e149-43f5-b1b5-b31e7c2ef5d4"

LEGACY_AMBIGUOUS = "CORE (E4) / DUO (E5) / DUO 1.5"

EKO_GENERATIONS = {
    LEGACY_SHARED_UUID: LEGACY_AMBIGUOUS,
    CORE2_UUID: "CORE2 (E6)",
    NORDIC_DFU_UUID: "Eko (Nordic bootloader)",
    DUO15_UUID: "DUO 1.5",
    DUO15_DFU_UUID: "DUO 1.5 (DFU)",
    DUO3_UUID: "DUO 3",
    DUO3_DFU_UUID: "DUO 3 (DFU)",
    CORE2_DFU_UUID: "CORE2 (DFU)",
}

EKO_DFU_UUIDS = (NORDIC_DFU_UUID, DUO15_DFU_UUID, DUO3_DFU_UUID, CORE2_DFU_UUID)

EKO_SERVICE_UUIDS = list(EKO_GENERATIONS)

_NORMALIZED_GENERATIONS = {
    _normalize_uuid(u): g for u, g in EKO_GENERATIONS.items()
}
_NORMALIZED_DFU = {_normalize_uuid(u) for u in EKO_DFU_UUIDS}
_NORMALIZED_LEGACY = _normalize_uuid(LEGACY_SHARED_UUID)

# Case-insensitive `contains` tiebreaks, most specific first.
_NAME_GENERATIONS = (
    ("eko core2", "CORE2 (E6)"),
    ("eko core", "CORE (E4)"),
    ("eko duo", "DUO (E5)"),
)

EKO_NAME_PATTERN = r"(?i)eko\s*(core|duo)"
_EKO_NAME_RE = re.compile(EKO_NAME_PATTERN)
_DFU_NAME_RE = re.compile(r"(?i)\b(dfu|required)\b")


@register_parser(
    name="eko_stethoscope",
    service_uuid=EKO_SERVICE_UUIDS,
    local_name_pattern=EKO_NAME_PATTERN,
    description="Eko digital stethoscopes (CORE / CORE2 / DUO / DUO 1.5 / DUO 3)",
    version="1.0.0",
    core=False,
)
class EkoStethoscopeParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        advertised = [_normalize_uuid(u) for u in (raw.service_uuids or [])]

        uuid_generation = None
        matched_uuid = None
        for uuid in advertised:
            if uuid in _NORMALIZED_GENERATIONS:
                uuid_generation = _NORMALIZED_GENERATIONS[uuid]
                matched_uuid = uuid
                break

        name = raw.local_name or ""
        name_hit = bool(_EKO_NAME_RE.search(name))

        if not (uuid_generation or name_hit):
            return None

        name_generation = None
        lowered = name.lower()
        for substring, generation in _NAME_GENERATIONS:
            if substring in lowered:
                name_generation = generation
                break

        ambiguous = False
        if uuid_generation is None:
            generation = name_generation
        elif matched_uuid == _NORMALIZED_LEGACY:
            # Shared legacy data service — the local name is the tiebreak.
            generation = name_generation or uuid_generation
            ambiguous = name_generation is None
        else:
            generation = uuid_generation

        dfu = (
            any(u in _NORMALIZED_DFU for u in advertised)
            or bool(_DFU_NAME_RE.search(name))
        )

        metadata: dict = {
            "vendor": "Eko",
            "telemetry": "connect_required",
            "dfu_mode": dfu,
            "generation_ambiguous": ambiguous,
        }
        if generation:
            metadata["generation"] = generation
        if matched_uuid:
            metadata["service_uuid"] = matched_uuid
        if name:
            metadata["device_name"] = name

        id_hash = hashlib.sha256(f"eko:{raw.mac_address}".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="eko_stethoscope",
            beacon_type="eko_stethoscope",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
