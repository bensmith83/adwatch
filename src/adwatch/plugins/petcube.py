"""Petcube BLE advertisement plugin — camera/feeder line + Petcube Tracker.

Per apk-ble-hunting/reports/petcube-android_passive.md (UUID table from the
companion Stage 4 report's `ServiceUuids.java` listing).

Two very different broadcast shapes share one vendor:

* **Camera / feeder line** (Petcube Cam, Play, Play 2, Bites, Bites 2/3) —
  discovery is by a **silicon-vendor-keyed 128-bit service UUID** advertised
  in the AD record (AD type 0x06/0x07). Nine UUIDs cover the Allwinner /
  Rockchip / Chicony SoC variants, so the matched UUID identifies both the
  model *and* the SoC vendor. Cameras only advertise while in Wi-Fi
  provisioning mode — a persistent broadcast means unprovisioned/factory-reset.
* **Petcube Tracker** — a Nordic-UART-based pet tag whose local name is
  ``TRACKER_`` + a **7-char per-tag suffix**. That suffix is the durable
  per-tag identifier (it survives MAC randomisation), so it is the identity
  hash basis. The bare NUS UUID ``6e400001-…`` is deliberately *not*
  registered: it is vendor-agnostic and would steal matches from every other
  Nordic-UART device.

Neither family broadcasts manufacturer data, service data, or telemetry.
"""

import hashlib
import re

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import _normalize_uuid, register_parser


# UUID -> (model, SoC vendor)
CAMERA_MODEL_BY_UUID = {
    "e7889b80-48e2-474e-8b6c-b585cc039b77": ("Petcube Bites", "Allwinner"),
    "b5cc439b-cfbd-4088-a606-86facc6c77fe": ("Petcube Bites", "Rockchip"),
    "1c9be4ef-7391-4d7b-a56c-44b0d87ee7c1": ("Petcube Bites 2", "Rockchip"),
    "66971b13-74ee-4ecd-aae8-cac5b756f2b7": ("Petcube Play 1.1", "unknown"),
    "4f375a04-5092-468e-9d88-be65f7bb9a3f": ("Petcube Play", "Allwinner"),
    "197e44bf-06e5-4a7e-95d7-b27e8c7f80ad": ("Petcube Play", "Allwinner (old)"),
    "edc968d2-10e7-4ad8-9b68-2c545aa3e7ca": ("Petcube Play", "Chicony"),
    "de180c5e-6bbd-11e7-907b-a6006ad3dba0": ("Petcube Play", "Rockchip"),
    "8f22fc9b-c180-43f4-ac04-d5b0a001ae77": ("Petcube Play 2", "Rockchip"),
}

PETCUBE_CAMERA_UUIDS = tuple(CAMERA_MODEL_BY_UUID)

_CAMERA_BY_NORM = {
    _normalize_uuid(u): v for u, v in CAMERA_MODEL_BY_UUID.items()
}

# `Regex("TRACKER_.+")` in the app, with a take-7 on the suffix.
PETCUBE_TRACKER_NAME_PATTERN = r"^TRACKER_[A-Za-z0-9]{7}$"
_TRACKER_RE = re.compile(PETCUBE_TRACKER_NAME_PATTERN)


@register_parser(
    name="petcube",
    service_uuid=list(PETCUBE_CAMERA_UUIDS),
    local_name_pattern=PETCUBE_TRACKER_NAME_PATTERN,
    description="Petcube pet camera / feeder (SoC-keyed UUID) and Petcube Tracker tag",
    version="1.0.0",
    core=False,
)
class PetcubeParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if raw.local_name:
            m = _TRACKER_RE.match(raw.local_name)
            if m:
                return self._parse_tracker(raw)

        for advertised in (raw.service_uuids or []):
            hit = _CAMERA_BY_NORM.get(_normalize_uuid(advertised))
            if hit:
                return self._parse_camera(raw, advertised, hit)

        return None

    def _parse_camera(self, raw, advertised, hit) -> ParseResult:
        model, soc = hit
        metadata: dict = {
            "vendor": "Petcube",
            "family": "camera",
            "model": model,
            "soc_vendor": soc,
            "service_uuid": _normalize_uuid(advertised),
            # Cameras stop advertising once provisioned onto Wi-Fi.
            "setup_mode": True,
        }
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        id_hash = hashlib.sha256(
            f"petcube:cam:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="petcube",
            beacon_type="petcube",
            device_class="camera",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def _parse_tracker(self, raw) -> ParseResult:
        suffix = raw.local_name[len("TRACKER_"):]
        metadata: dict = {
            "vendor": "Petcube",
            "family": "tracker",
            "model": "Petcube Tracker",
            "tracker_id": suffix,
            "device_name": raw.local_name,
        }

        stable_key = f"petcube:tracker:{suffix}"
        id_hash = hashlib.sha256(stable_key.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="petcube",
            beacon_type="petcube",
            device_class="pet_tracker",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
            stable_key=stable_key,
        )

    def storage_schema(self):
        return None
