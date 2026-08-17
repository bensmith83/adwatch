"""Shearwater dive computer advertisement parser.

Per apk-ble-hunting/reports/shearwater-cloud_passive.md.

Shearwater Cloud scans unfiltered at the OS layer and filters in software on
an **exact device-name allow-list** (`DiveComputerFilter.java:11,52`) plus a
two-character MAC prefix (`10`/`13`, `DiveComputerFilter.java:27-33`). There
is no manufacturer-data or service-data parsing anywhere on its scan path,
and no telemetry in the advert — only presence and the model, which the name
gives away verbatim.

Matching notes:

* the name allow-list is matched **exactly** (anchored), so `Petrel Pro` or
  `My Teric` do not claim a sighting;
* the `10`/`13` MAC prefix is deliberately **not** registered. It covers a
  whole address space (and half of it is not even a valid public OUI), so
  registering it would claim every nameless device that happens to land
  there. It is reported as corroborating metadata instead, and only when the
  address is public — which is the property the app's heuristic actually
  relies on;
* SIG CID `0x1064` (Shearwater Research Inc.) and the two DCCP service UUIDs
  are registered so a live capture that does carry them still routes here,
  even though the APK reads neither.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import _normalize_uuid, register_parser


# SIG company ID for "Shearwater Research Inc." (_bt_company_ids.py:0x1064).
SHEARWATER_COMPANY_ID = 0x1064

DCCP2_UUID = "1aa44039-1667-4b29-87cc-dfecaaf31d97"
DCCP1_UUID = "fe25c237-0ece-443c-b0aa-e02033e7029d"
SHEARWATER_SERVICE_UUIDS = [DCCP2_UUID, DCCP1_UUID]
_DCCP_NAMES = {
    _normalize_uuid(DCCP2_UUID): "DCCP2",
    _normalize_uuid(DCCP1_UUID): "DCCP1",
}

# Exact advertised local names -> model family (DiveComputerFilter.java:11).
SHEARWATER_MODELS = {
    "Tern": "Tern",
    "Tern Tx": "Tern",
    "Teric": "Teric",
    "Petrel": "Petrel",
    "Petrel 2": "Petrel",
    "Petrel 3": "Petrel",
    "Perdix": "Perdix",
    "Perdix 2": "Perdix",
    "Perdix 3": "Perdix",
    "Perdix AI": "Perdix",
    "Peregrine": "Peregrine",
    "Peregrine TX": "Peregrine",
    "NERD": "NERD",
    "NERD 2": "NERD",
    "Predator": "Predator",
}

SHEARWATER_MAC_PREFIXES = ("10", "13")

SHEARWATER_NAME_PATTERN = r"^(?:" + "|".join(
    re.escape(n) for n in sorted(SHEARWATER_MODELS, key=len, reverse=True)
) + r")$"
_SHEARWATER_NAME_RE = re.compile(SHEARWATER_NAME_PATTERN)


@register_parser(
    name="shearwater",
    company_id=SHEARWATER_COMPANY_ID,
    service_uuid=SHEARWATER_SERVICE_UUIDS,
    local_name_pattern=SHEARWATER_NAME_PATTERN,
    description="Shearwater dive computers (Petrel / Perdix / Teric / Peregrine / NERD / Tern)",
    version="1.0.0",
    core=False,
)
class ShearwaterParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        name = raw.local_name or ""
        name_hit = bool(_SHEARWATER_NAME_RE.match(name))

        dccp = None
        for uuid in (raw.service_uuids or []):
            dccp = _DCCP_NAMES.get(_normalize_uuid(uuid))
            if dccp:
                break

        has_cid = (
            raw.manufacturer_data is not None
            and len(raw.manufacturer_data) >= 2
            and raw.company_id == SHEARWATER_COMPANY_ID
        )

        if not (name_hit or dccp or has_cid):
            return None

        metadata: dict = {
            "vendor": "Shearwater",
            "telemetry": "connect_required_dccp",
            "mac_prefix_match": (
                raw.mac_type == "public"
                and raw.mac_address.upper().startswith(SHEARWATER_MAC_PREFIXES)
            ),
        }
        if name:
            metadata["device_name"] = name
        if name_hit:
            metadata["model"] = name
            metadata["model_family"] = SHEARWATER_MODELS[name]
        if dccp:
            metadata["dccp_service"] = dccp
        if has_cid:
            metadata["company_id_hex"] = f"0x{SHEARWATER_COMPANY_ID:04X}"
            if raw.manufacturer_payload:
                metadata["manufacturer_payload_hex"] = raw.manufacturer_payload.hex()

        # No per-unit identifier is broadcast; these units use a static public
        # address, so the MAC is the stable key.
        id_hash = hashlib.sha256(
            f"shearwater:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="shearwater",
            beacon_type="shearwater",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
