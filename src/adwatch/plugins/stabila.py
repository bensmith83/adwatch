"""STABILA laser distance measure ("Disto") plugin.

Per apk-ble-hunting/reports/stabila-measures_passive.md (com.stabila.measures).

The app is Flutter and its advertisement-parsing logic lives inside the Dart
snapshot ``libapp.so``, so **no manufacturer-data or service-data byte layout
is recoverable** — the report explicitly flags both as "needs a Stage 6d Dart
decompile". What *is* statically confirmed is the scan filter:

* custom 128-bit service UUID ``3ab10100-f831-4395-b29d-570977d5bf94``
  (characteristics ``3ab10101``..``3ab10104`` live under it), and
* the advertised model name ``Stabila LD 250 BT`` (a case-insensitive
  startsWith keyword filter is used app-side).

Both are highly distinctive, so this is a presence/identity parser: it names
the device and surfaces any manufacturer/service-data bytes undecoded so they
show up in the Protocol Explorer for future reverse engineering. The name is a
per-*model* string with no serial suffix, so identity falls back to the BLE MAC
(the report notes STABILA does not rotate it).
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import _normalize_uuid, register_parser


STABILA_SERVICE_UUID = "3ab10100-f831-4395-b29d-570977d5bf94"
STABILA_NAME_RE = r"(?i)^stabila\b"

_STABILA_UUID_NORM = _normalize_uuid(STABILA_SERVICE_UUID)
_NAME_MODEL_RE = re.compile(r"(?i)^stabila\s+(.+?)\s*$")

# Model strings recovered from libapp.so.
PRODUCT_FAMILIES = {
    "LD 250 BT": "LD 250 BT laser distance measure",
    "LD 520": "LD 520 laser distance measure",
}


@register_parser(
    name="stabila",
    service_uuid=STABILA_SERVICE_UUID,
    local_name_pattern=STABILA_NAME_RE,
    description="STABILA laser distance measures (LD 250 BT / LD 520)",
    version="1.0.0",
    core=False,
)
class StabilaParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        uuid_hit = any(
            _normalize_uuid(u) == _STABILA_UUID_NORM
            for u in (raw.service_uuids or [])
        ) or any(
            _normalize_uuid(k) == _STABILA_UUID_NORM
            for k in (raw.service_data or {})
        )
        name_hit = bool(raw.local_name and re.search(STABILA_NAME_RE, raw.local_name))

        if not (uuid_hit or name_hit):
            return None

        metadata: dict = {
            "vendor": "STABILA",
            "service_uuid_match": uuid_hit,
        }

        if raw.local_name:
            metadata["device_name"] = raw.local_name
            m = _NAME_MODEL_RE.match(raw.local_name)
            if m:
                model = re.sub(r"\s+", " ", m.group(1))
                metadata["model"] = model
                family = PRODUCT_FAMILIES.get(model.upper())
                if family:
                    metadata["product_family"] = family

        # Byte layouts are unknown (Dart snapshot) — surface raw bytes so they
        # land in the Protocol Explorer instead of being dropped.
        if raw.manufacturer_data and len(raw.manufacturer_data) >= 2:
            metadata["company_id"] = raw.company_id
            payload = raw.manufacturer_payload
            if payload:
                metadata["payload_hex"] = payload.hex()

        for key, val in (raw.service_data or {}).items():
            if _normalize_uuid(key) == _STABILA_UUID_NORM:
                metadata["service_data_hex"] = val.hex()
                break

        id_hash = hashlib.sha256(
            f"stabila:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="stabila",
            beacon_type="stabila",
            device_class="measuring_tool",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
