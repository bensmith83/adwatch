"""Specialized Turbo (Mission Control) e-bike advertisement parser.

Per apk-ble-hunting/reports/specialized-turbo_passive.md.

Mission Control is a Qt-Android app whose scan-filter logic lives in
``libmission_control.so`` (``apis::bca::DeviceScannerFilter::isLevoTurboDevice``),
so no scan filter is recoverable from the Java surface. Two things *are*
recoverable and distinctive:

1. **Two vendor UUID schemes** whose tail bytes are ASCII vendor signatures:

   * scheme A ``0000XXXX-0000-4B49-4E4F-525441474947`` — tail decodes to
     ``KINORTAGIG`` = "GIGATRONIK" reversed (the controller-stack vendor);
   * scheme B ``0000XXXX-3731-3032-494D-484F42525554`` — tail decodes to
     ``7102IMHOBRUT`` = "TURBOHMI2017" reversed.

   The 16-bit slot ``XXXX`` varies per service, and the registry only does
   exact UUID matching, so we register the low slots ``0x0000``-``0x000F`` of
   both schemes and additionally suffix-check *every* advertised UUID inside
   ``parse()`` — that way an unenumerated slot still decodes whenever the
   advert reaches us by any route.

2. **A model/serial local name.** ``DeviceScannerFilter::setSerialIdForTurboLevo``
   plus ``ConnectionManager::deviceName()`` imply name-based, per-bike-serial
   filtering. The exact string shape is inference (Ghidra/live capture would
   confirm), so the name regex is limited to Specialized-specific model words.

No manufacturer data or service data is emitted by the bike as far as static
analysis shows; telemetry is GATT-only after connect.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import _normalize_uuid, register_parser


# Tail bytes: b"\x00\x00KINORTAGIG" ("GIGATRONIK" reversed).
SCHEME_A_SUFFIX = "-0000-4b49-4e4f-525441474947"
# Tail bytes: b"7102IMHOBRUT" ("TURBOHMI2017" reversed).
SCHEME_B_SUFFIX = "-3731-3032-494d-484f42525554"

SCHEME_NAMES = {
    SCHEME_A_SUFFIX: "gigatronik",
    SCHEME_B_SUFFIX: "turbo_hmi_2017",
}

# The registry needs exact UUIDs; enumerate the plausible low service slots.
SPECIALIZED_SERVICE_UUIDS = [
    f"0000{slot:04x}{suffix}"
    for suffix in (SCHEME_A_SUFFIX, SCHEME_B_SUFFIX)
    for slot in range(0x10)
]

SPECIALIZED_NAME_PATTERN = (
    r"^(?i:specialized|turbo[ _-]?(?:levo|vado|como|kenevo|creo|tero|sl)|levo|kenevo)\b"
)
_NAME_RE = re.compile(SPECIALIZED_NAME_PATTERN)
_MODEL_RE = re.compile(
    r"^(Specialized|Turbo[ _-]?(?:Levo|Vado|Como|Kenevo|Creo|Tero|SL)|Levo|Kenevo)",
    re.I,
)
_SERIAL_RE = re.compile(r"[ _-]([A-Za-z0-9]{4,})$")


def scheme_for_uuid(uuid: str) -> str | None:
    """Return the Specialized UUID-scheme name for `uuid`, or None."""
    normalized = _normalize_uuid(uuid)
    if not isinstance(normalized, str):
        return None
    for suffix, scheme in SCHEME_NAMES.items():
        if normalized.endswith(suffix):
            return scheme
    return None


@register_parser(
    name="specialized_turbo",
    service_uuid=SPECIALIZED_SERVICE_UUIDS,
    local_name_pattern=SPECIALIZED_NAME_PATTERN,
    description="Specialized Turbo e-bikes (Levo / Vado / Como / Kenevo / Creo)",
    version="1.0.0",
    core=False,
)
class SpecializedTurboParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        scheme = None
        matched_uuid = None
        for uuid in (raw.service_uuids or []):
            scheme = scheme_for_uuid(uuid)
            if scheme:
                matched_uuid = _normalize_uuid(uuid)
                break

        name = raw.local_name or ""
        name_hit = bool(_NAME_RE.match(name))

        if not (scheme or name_hit):
            return None

        metadata: dict = {"vendor": "Specialized"}
        if scheme:
            metadata["uuid_scheme"] = scheme
            metadata["service_uuid"] = matched_uuid
            metadata["service_slot"] = matched_uuid[4:8]

        serial = None
        if name:
            metadata["device_name"] = name
        if name_hit:
            model = _MODEL_RE.match(name)
            if model:
                metadata["model"] = model.group(1)
            serial_match = _SERIAL_RE.search(name)
            if serial_match:
                serial = serial_match.group(1)
                metadata["serial"] = serial

        if serial:
            id_basis = f"specialized:{serial}"
        else:
            id_basis = f"specialized:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="specialized_turbo",
            beacon_type="specialized_turbo",
            device_class="vehicle",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
