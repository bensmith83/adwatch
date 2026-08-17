"""Bird Buddy smart bird-feeder BLE advertisement plugin.

Per apk-ble-hunting/reports/birdbuddy-app_passive.md (scan filters recovered
from the Hermes bytecode with droidsaw). BLE is used only during Wi-Fi
onboarding; once provisioned the feeder moves to Wi-Fi/WebRTC, so a
broadcasting feeder is a "needs setup" signal.

Discovery:

* **Local name contains ``BUDDY``** (case-sensitive substring test in
  ``handleDiscoverPeripheral``), usually with a leading ``Bb`` that the app
  strips for display via ``removeBbPrefix``.
* **V1 feeders** also advertise ``8a7f1168-48af-4efb-83b5-e679f932ff00``.
* **V2 feeders** (``a9d7166a-d72e-40a9-a002-48044cc30100``) are matched by
  name; their service is confirmed only after connecting.

Both 128-bit UUIDs above are in fact **AmazonFreeRTOS SDK service UUIDs**,
not Bird Buddy ones -- the same pair appears in Pentair Home's bundle (see
``plugins/amazon_freertos.py`` and
``reports/pentair-pentairhome_passive.md``, which names ``8a7f1168-...ff00``
the AmazonFreeRTOS DEVICE_INFO service). They still make a Bird Buddy V1
findable, so they stay registered, but a UUID-only hit is flagged
``uuid_is_shared_afr_service`` / ``confidence: low`` because a Pentair salt
cell would look identical. The ``BUDDY`` name is what makes the call
confident.

The report also lists SIG-base shorts ``0000ff01`` and ``0000a00a`` for V1.
Neither is registered as a match criterion: ``ff01`` is generic and ``a00a``
is already claimed by ``meross.py``. They are recorded as ``weak_uuid_hits``
when some stronger signal already matched.

Manufacturer data and service data are not used by the app. The debunked
Stage-4 candidate ``d19b16d9-ff90-4606-854d-a6d0efe56cb3`` is deliberately
absent — the report marks it a byte-proximity artifact.
"""

import hashlib
import re

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import _normalize_uuid, register_parser


BIRDBUDDY_V1_UUID = "8a7f1168-48af-4efb-83b5-e679f932ff00"
BIRDBUDDY_V2_UUID = "a9d7166a-d72e-40a9-a002-48044cc30100"

# Listed for V1 but too generic / already claimed to match on.
BIRDBUDDY_WEAK_UUIDS = (
    "0000ff01-0000-1000-8000-00805f9b34fb",
    "0000a00a-0000-1000-8000-00805f9b34fb",
)

_V1_NORM = _normalize_uuid(BIRDBUDDY_V1_UUID)
_V2_NORM = _normalize_uuid(BIRDBUDDY_V2_UUID)
_WEAK_NORM = {_normalize_uuid(u) for u in BIRDBUDDY_WEAK_UUIDS}

# Case-sensitive "BUDDY", anchored so an unrelated device that merely
# contains the word is not claimed.
BIRDBUDDY_NAME_PATTERN = r"^(?:Bb.*BUDDY|BUDDY)"

_BB_PREFIX = "Bb"
_NAME_RE = re.compile(BIRDBUDDY_NAME_PATTERN)


@register_parser(
    name="birdbuddy",
    service_uuid=[BIRDBUDDY_V1_UUID, BIRDBUDDY_V2_UUID],
    local_name_pattern=BIRDBUDDY_NAME_PATTERN,
    description="Bird Buddy smart bird-feeder camera (Wi-Fi onboarding beacon)",
    version="1.0.0",
    core=False,
)
class BirdBuddyParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        advertised = [_normalize_uuid(u) for u in (raw.service_uuids or [])]
        v1_hit = _V1_NORM in advertised
        v2_hit = _V2_NORM in advertised
        name = raw.local_name
        name_hit = bool(name and _NAME_RE.match(name))

        # The two UUIDs are AmazonFreeRTOS SDK services shared with every
        # AFR-based product (Pentair salt cells, ...). Without the Bird Buddy
        # name the sighting belongs to plugins/amazon_freertos.py; here the
        # UUIDs only refine the hardware revision.
        if not name_hit:
            return None

        if v1_hit:
            revision = "V1"
        elif v2_hit:
            revision = "V2"
        else:
            revision = "unknown"

        metadata: dict = {
            "vendor": "Bird Buddy",
            "model": "Bird Buddy smart feeder",
            "hardware_revision": revision,
            # BLE only runs during onboarding.
            "setup_mode": True,
            "confidence": "high",
        }
        if name:
            metadata["device_name"] = name
            metadata["display_name"] = (
                name[len(_BB_PREFIX):] if name.startswith(_BB_PREFIX) else name
            )
        weak = [u for u in advertised if u in _WEAK_NORM]
        if weak:
            metadata["weak_uuid_hits"] = weak

        id_hash = hashlib.sha256(
            f"birdbuddy:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="birdbuddy",
            beacon_type="birdbuddy",
            device_class="camera",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
