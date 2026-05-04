"""Wahoo Fitness plugin (TICKR / KICKR / ELEMNT / HEADWIND / TRACKR / POWRLINK).

Per apk-ble-hunting/reports/wahoofitness-fitness_passive.md. Identifies
Wahoo-branded BLE peripherals via three signals (OR-logic):

  - **Wahoo CID 0x01FC** (508 — Wahoo Fitness, SIG-assigned)
  - **Wahoo proprietary 16-bit service UUIDs**: ``0xEE06`` (ELEMNT),
    ``0xEE07`` (legacy WAHOO_GYM_CONNECT), ``0xEE0A`` (DFU mode),
    ``0xEE0D`` (KICKR BIKE), ``0xEE0E`` (treadmill), ``0xEE0F``
    (POWRLINK power pedals)
  - **Device-name regex catalog** covering Wahoo product families with
    a 4-6 char hex serial suffix used as a stable identity-hash basis.

Generic SIG sensor profile UUIDs (HR 0x180D, FTMS 0x1826, etc.) are NOT
matched here — they're vendor-agnostic and would steal sightings from
non-Wahoo sensors. A future generic-fitness plugin could handle them.

Mfr-data decode for ELEMNT / FTMS variants when the Wahoo CID is present:
``payload[0..1]`` = product_id (uint16 LE) and ``payload[2..3]`` =
hw_version (uint16 LE) — see report's BluetoothLeAdvData.create() table.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


WAHOO_CID = 0x01FC  # 508

WAHOO_SERVICE_UUIDS = ["ee06", "ee07", "ee0a", "ee0d", "ee0e", "ee0f"]
_WAHOO_FULL_UUIDS = {
    f"0000{u}-0000-1000-8000-00805f9b34fb": u for u in WAHOO_SERVICE_UUIDS
}

_DFU_UUID = "ee0a"

# Family-prefix regex (anchored). Order: longest prefixes first so e.g.
# "KICKR BIKE" wins over "KICKR".
_FAMILY_PATTERNS = [
    ("KICKR_BIKE", re.compile(r"^KICKR BIKE(?: JR)? (?P<serial>[0-9A-Fa-f]{4,6})$")),
    ("KICKR", re.compile(r"^KICKR (?P<serial>[0-9A-Fa-f]{4,6})$")),
    ("ELEMNT", re.compile(r"^ELEMNT(?: (?:BOLT|ROAM|MINI|RIVAL|ACE))? (?P<serial>[0-9A-Fa-f]{4,6})$")),
    ("TICKR", re.compile(r"^TICKR(?: X| RUN| FIT)? (?P<serial>[0-9A-Fa-f]{4,6})$")),
    ("TRACKR", re.compile(r"^TRACKR(?: HR| RADAR| SPEED)? (?P<serial>[0-9A-Fa-f]{4,6})$")),
    ("HEADWIND", re.compile(r"^HEADWIND (?P<serial>[0-9A-Fa-f]{4,6})$")),
    ("POWRLINK", re.compile(r"^POWRLINK(?: ZERO)? (?P<serial>[0-9A-Fa-f]{4,6})$")),
    ("RUNNR", re.compile(r"^RUNNR (?P<serial>[0-9A-Fa-f]{4,6})$")),
    ("MIRROR", re.compile(r"^MIRROR (?P<serial>[0-9A-Fa-f]{4,6})$")),
    ("RFLKT", re.compile(r"^RFLKT$")),
    ("Dreadmill", re.compile(r"^Dreadmill(?: (?P<serial>[0-9A-Fa-f]{4,6}))?$")),
]

# Bare-prefix fallback for products that ship under a single family
# without a serial suffix (or with a different suffix style we haven't
# captured yet).
_FALLBACK_RE = re.compile(r"^(TICKR|KICKR|ELEMNT|HEADWIND|POWRLINK|TRACKR|RFLKT|RUNNR|MIRROR|Dreadmill)\b")


@register_parser(
    name="wahoo",
    company_id=WAHOO_CID,
    service_uuid=WAHOO_SERVICE_UUIDS,
    local_name_pattern=r"^(TICKR|KICKR|ELEMNT|HEADWIND|POWRLINK|TRACKR|RFLKT|RUNNR|MIRROR|Dreadmill)",
    description="Wahoo Fitness sensors / trainers / cycling computers",
    version="1.0.0",
    core=False,
)
class WahooParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        cid_hit = raw.company_id == WAHOO_CID
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        wahoo_uuid: str | None = None
        for short in WAHOO_SERVICE_UUIDS:
            if short in normalized:
                wahoo_uuid = short
                break
            for full, mapped in _WAHOO_FULL_UUIDS.items():
                if full in normalized:
                    wahoo_uuid = mapped
                    break
            if wahoo_uuid:
                break

        local_name = raw.local_name or ""
        family: str | None = None
        serial: str | None = None
        for fam, pat in _FAMILY_PATTERNS:
            m = pat.match(local_name)
            if m:
                family = fam.split("_", 1)[0]
                if "serial" in m.groupdict() and m.group("serial"):
                    serial = m.group("serial")
                break
        if family is None:
            fb = _FALLBACK_RE.match(local_name)
            if fb:
                family = fb.group(1)

        if not (cid_hit or wahoo_uuid or family):
            return None

        metadata: dict = {"vendor": "Wahoo"}
        if family:
            metadata["product_family"] = family
            metadata["device_name"] = local_name
        if serial:
            metadata["serial_suffix"] = serial
        if wahoo_uuid == _DFU_UUID:
            metadata["dfu_mode"] = True
        if wahoo_uuid:
            metadata["wahoo_service_uuid"] = wahoo_uuid

        if cid_hit:
            payload = raw.manufacturer_payload or b""
            if len(payload) >= 2:
                metadata["product_id"] = int.from_bytes(payload[0:2], "little")
            if len(payload) >= 4:
                metadata["hw_version"] = int.from_bytes(payload[2:4], "little")

        if family and serial:
            id_basis = f"wahoo:{family}:{serial}"
        elif family:
            id_basis = f"wahoo:{family}:{raw.mac_address}"
        else:
            id_basis = f"wahoo:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="wahoo",
            beacon_type="wahoo",
            device_class="fitness_sensor",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
