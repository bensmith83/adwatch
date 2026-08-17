"""Fellow "EKG" smart-kettle plugin (Stagg EKG / EKG+ / EKG Pro, Corvo EKG).

Per apk-ble-hunting/reports/fellowapp_passive.md: Fellow's kettles are
ESP32-based and advertise a custom 128-bit primary service UUID. The
companion app filters by service UUID; an aux UUID also appears in some
ads (likely OTA / provisioning). Mfr-data is not used in static analysis;
the local-name carries the model and may include a MAC-suffix tail like
``Stagg EKG Pro-A1B2``.

**v1.1.0 (2026-08-17) — the ``EKG-<hex tail>`` setup beacon.** The
``EKG-XX-XX-XX`` local-name family (e.g. ``EKG-99-23-4c``, 959k+ sightings
of one unit) was documented as "medical EKG" and routed to
``alivecor_ekg.py`` for a long time. That was a guess from the "EKG" token;
the evidence points here:

  * Fellow's kettle line is literally named EKG ("Electric Kettle
    Gooseneck"): Stagg EKG, Stagg EKG+, Stagg EKG Pro, Corvo EKG.
  * The unit advertises solely the Espressif Wi-Fi-provisioning service UUID
    ``021a9004-0382-4aea-bff4-6b3f1c5adfb4`` — Fellow's connected kettles are
    ESP32-based; AliveCor's Kardia devices are not.
  * The old research doc listed ``7aebf330-6cb1-46e4-b23b-7cc2262c605e`` as
    a second "EKG" UUID — that is ``FELLOW_AUX_UUID`` from the decompiled
    Fellow app.
  * Genuine AliveCor Kardia hardware advertises ``ac060001-…``/``ac010001-…``
    with ``KardiaMobile_*``/``KardiaCard_*`` names — never ``EKG-``.

Match rules (any one suffices; a PRESENT non-Fellow name is always rejected
so the plugin stays name-gate safe):

  A) name ``EKG-<hex pairs>`` (setup / provisioning beacon; the tail is a
     per-unit id baked into the GAP name and survives MAC rotation)
  B) name ``Stagg EKG Pro[-XXXX]`` / ``Corvo EKG[-XXXX]`` / ``Fellow EKG Pro[-XXXX]``
  C) either Fellow 128-bit service UUID, no name

The Espressif provisioning UUID is NEVER a match key here (``espressif_prov``
owns it); it is surfaced as ``provisioning_mode`` when it accompanies a
Fellow name. Day-to-day a paired kettle may stop advertising, so a hit
generally means the device is in pair / setup mode. ``match_basis`` records
exactly which signals fired.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


FELLOW_PRIMARY_UUID = "2291c4b6-5d7f-4477-a88b-b266edb97142"
FELLOW_AUX_UUID = "7aebf330-6cb1-46e4-b23b-7cc2262c605e"
# Corroboration only — owned by espressif_prov.py, never a match key here.
ESPRESSIF_PROV_UUID = "021a9004-0382-4aea-bff4-6b3f1c5adfb4"

# Routing pattern: EKG-<hex pairs> setup beacon OR a model name.
FELLOW_NAME_PATTERN = (
    r"^(EKG-[0-9A-Fa-f]{2}(-[0-9A-Fa-f]{2})+$|Stagg EKG Pro|Corvo EKG|Fellow EKG Pro)"
)

_EKG_TAIL_RE = re.compile(r"^EKG-([0-9A-Fa-f]{2}(?:-[0-9A-Fa-f]{2})+)$")
_MODEL_RE = re.compile(
    r"^(Stagg EKG Pro|Corvo EKG|Fellow EKG Pro)(?:-([0-9A-Fa-f]{2,8}))?$"
)


@register_parser(
    name="fellow",
    service_uuid=[FELLOW_PRIMARY_UUID, FELLOW_AUX_UUID],
    local_name_pattern=FELLOW_NAME_PATTERN,
    description="Fellow Stagg / Corvo EKG smart kettles",
    version="1.1.0",
    core=False,
)
class FellowParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        primary_hit = FELLOW_PRIMARY_UUID in normalized
        aux_hit = FELLOW_AUX_UUID in normalized
        prov_hit = ESPRESSIF_PROV_UUID in normalized
        local_name = raw.local_name or ""

        metadata: dict = {"vendor": "Fellow"}
        basis: list[str] = []
        unit_id: str | None = None

        if local_name:
            ekg = _EKG_TAIL_RE.match(local_name)
            model_m = _MODEL_RE.match(local_name)
            if ekg:
                unit_id = ekg.group(1)
                metadata["device_id"] = unit_id
                metadata["device_name"] = local_name
                metadata["model_hint"] = "Stagg EKG / Corvo EKG (setup beacon)"
                basis.append("name_ekg_tail")
            elif model_m:
                metadata["model"] = model_m.group(1)
                metadata["device_name"] = local_name
                if model_m.group(2):
                    unit_id = model_m.group(2).upper()
                    metadata["mac_suffix"] = unit_id
                basis.append("name_model")
            else:
                # A present name that is not a Fellow token: never claim it,
                # even with a Fellow UUID.
                return None
        elif not (primary_hit or aux_hit):
            return None

        if primary_hit:
            basis.append("primary_uuid")
        if aux_hit:
            metadata["aux_service_seen"] = True
            basis.append("aux_uuid")
        if prov_hit:
            metadata["provisioning_mode"] = True
            basis.append("espressif_prov_uuid")
        metadata["match_basis"] = "+".join(basis)

        if unit_id:
            id_basis = f"fellow:{unit_id}"
        else:
            id_basis = f"fellow:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="fellow",
            beacon_type="fellow",
            device_class="kettle",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
