"""Therabody PowerDot / SmartMio EMS pod plugin.

Per apk-ble-hunting/reports/therabody-powerdot_passive.md.

The app does no advertisement decoding at all (there is no
``android.bluetooth.le`` usage anywhere in the tree). The only broadcast
attribute it relies on is the device name, matched by **prefix**
(``FirmwareProtocol.isSupport()`` uses ``indexOf(prefix) == 0``):

  ``PowerDot2`` (v2), ``PowerDotMT`` (v2mt medical firmware), and the GEN-1
  set ``GEN_1`` / ``aPowerDot`` / ``SmartMio`` / ``aSmartMio`` (v1).

Two vendor service UUIDs are known from the GATT layer and are also registered,
since if the pod advertises one it is a stronger, name-independent filter — the
report flags this as unverified, so a UUID-only hit reports no model.

Prefix matching implies a per-device suffix (serial / MAC fragment) after the
brand prefix. That suffix is a persistent broadcast identifier, so it is
preferred over the MAC for the identity hash (``identity_basis`` records which
was used). Duo kits are disambiguated by the app *after* connecting, not from
the advertisement.

No state is broadcast: battery (``b``), firmware (``?``), readiness (``r``) and
stimulation status are all connected-mode ASCII-protocol responses.

Privacy: presence discloses a muscle-stim / recovery device, and the stable
name makes a specific pod trackable. Flagged ``sensitive=True``.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


POWERDOT_STIM_SERVICE_UUID = "9eca0001-0ee5-a9e0-93f3-a3b50100406e"
POWERDOT_LEGACY_SERVICE_UUID = "c14d2c0a-401f-b7a9-841f-e2e93b80f631"
POWERDOT_SERVICE_UUIDS = [
    POWERDOT_STIM_SERVICE_UUID,
    POWERDOT_LEGACY_SERVICE_UUID,
]

# (lowercase prefix, model, protocol generation, confidence). Ordered so the
# longer/more specific prefixes are tested first.
_NAME_PREFIXES = (
    ("powerdotmt", "PowerDot MT", "v2mt", "high"),
    ("powerdot2", "PowerDot 2.0", "v2", "high"),
    ("apowerdot", "PowerDot (GEN-1)", "v1", "high"),
    ("asmartmio", "SmartMio (GEN-1)", "v1", "high"),
    ("smartmio", "SmartMio (GEN-1)", "v1", "high"),
    # `GEN_1` is a generic-looking prefix — kept, but at lower confidence.
    ("gen_1", "PowerDot (GEN-1)", "v1", "medium"),
)
POWERDOT_NAME_PATTERN = (
    r"(?i)^(PowerDotMT|PowerDot2|aPowerDot|aSmartMio|SmartMio|GEN_1)"
)


@register_parser(
    name="powerdot",
    service_uuid=POWERDOT_SERVICE_UUIDS,
    local_name_pattern=POWERDOT_NAME_PATTERN,
    description="Therabody PowerDot / SmartMio EMS pod (presence-only)",
    version="1.0.0",
    core=False,
)
class PowerDotParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        if raw.service_data:
            normalized += [k.lower() for k in raw.service_data]
        uuid_hit = next(
            (u for u in POWERDOT_SERVICE_UUIDS if u in normalized), None
        )

        local_name = (raw.local_name or "").strip()
        lowered = local_name.lower()
        name_entry = next(
            (e for e in _NAME_PREFIXES if lowered.startswith(e[0])), None
        )

        if name_entry is None and uuid_hit is None:
            return None

        metadata: dict = {
            "vendor": "Therabody",
            "telemetry": "none (connect-only GATT)",
            "sensitive": True,
            "sensitive_category": "muscle_stimulation",
        }
        if local_name:
            metadata["device_name"] = local_name

        if name_entry is not None:
            prefix, model, generation, confidence = name_entry
            metadata["model"] = model
            metadata["protocol_generation"] = generation
            metadata["name_prefix"] = local_name[: len(prefix)]
            metadata["name_suffix"] = local_name[len(prefix):]
            metadata["match_basis"] = "local_name"
            metadata["confidence"] = "high" if uuid_hit else confidence
        else:
            # UUID-only: the report does not confirm the pod advertises it, and
            # it carries no model information, so claim nothing further.
            metadata["match_basis"] = "service_uuid"
            metadata["confidence"] = "medium"
        if uuid_hit is not None:
            metadata["service_uuid"] = uuid_hit

        # The per-device name suffix is a persistent broadcast identifier —
        # prefer it over the MAC.
        suffix = metadata.get("name_suffix") or ""
        if suffix:
            id_basis = f"powerdot:{local_name}"
            metadata["identity_basis"] = "local_name"
        else:
            id_basis = f"powerdot:{raw.mac_address}"
            metadata["identity_basis"] = "mac"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="powerdot",
            beacon_type="powerdot",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
