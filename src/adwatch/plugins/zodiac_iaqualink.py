"""Zodiac iAquaLink pool / spa equipment plugin (Zodiac / Jandy / Polaris).

Per apk-ble-hunting/reports/zodiac-iaqualink_passive.md, discovery is
service-UUID + name-prefix only -- the app parses no manufacturer data and
no service data:

* OS-level scan filter on the advertised vendor service UUID
  ``3D3A3B57-91AA-4344-810C-66C7E964ABEF`` (`UUIDConstants.java:24`,
  `BleConnectViewModel.java:136-146`).
* Post-filter on the per-family advertised-name prefixes
  (`UUIDConstants.java:18-20`): ``iAqua_`` (TCX controller),
  ``vortrax`` (Vortrax/Vax), ``robotic_cleaner`` (VRF cleaner). The
  CycloNext / ZS500 / Blue / CycloBat prefixes were not recoverable.

Do not confuse the advertised UUID with the GATT primary service
``49535343-FE7D-4AE5-8FA9-9FAFD205E455`` (Microchip ISSC transparent
UART). That one only exists post-connect, is shared by many unrelated
vendors, and is deliberately NOT registered here.

All pool state (mode, setpoints, equipment status) rides the post-connect
JSON-over-BLE protocol, so nothing about pool activity leaks passively.
What does leak is the household's ownership of a Zodiac pool system plus a
durable per-unit serial in the name suffix, which is the identity basis
here (falling back to the BLE MAC when only the UUID is seen).
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


ZODIAC_ADV_SERVICE_UUID = "3d3a3b57-91aa-4344-810c-66c7e964abef"

ZODIAC_NAME_PATTERN = r"(?i)^(iAqua_|vortrax|robotic_cleaner)"

# prefix regex -> (family key, model label, device class)
_FAMILIES = [
    (re.compile(r"(?i)^iAqua_"), "tcx_controller",
     "Zodiac TCX pool/spa controller", "pool_controller"),
    (re.compile(r"(?i)^vortrax"), "vortrax",
     "Zodiac Vortrax / Vax cleaner", "pool_cleaner"),
    (re.compile(r"(?i)^robotic_cleaner"), "vrf_robotic_cleaner",
     "Zodiac VRF robotic cleaner", "pool_cleaner"),
]


@register_parser(
    name="zodiac_iaqualink",
    service_uuid=ZODIAC_ADV_SERVICE_UUID,
    local_name_pattern=ZODIAC_NAME_PATTERN,
    description="Zodiac iAquaLink pool controllers and robotic cleaners",
    version="1.0.0",
    core=False,
)
class ZodiacIAquaLinkParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        uuid_hit = ZODIAC_ADV_SERVICE_UUID in normalized
        if not uuid_hit and raw.service_data:
            uuid_hit = any(k.lower() == ZODIAC_ADV_SERVICE_UUID
                           for k in raw.service_data)

        name = raw.local_name or ""
        family = model = None
        device_class = "pool_controller"
        suffix = None
        for pattern, family_key, label, klass in _FAMILIES:
            m = pattern.match(name)
            if m:
                family, model, device_class = family_key, label, klass
                tail = name[m.end():].lstrip("_")
                if tail:
                    suffix = tail
                break

        if not (uuid_hit or family):
            return None

        metadata: dict = {
            "vendor": "Zodiac",
            "brand_family": "Zodiac/Jandy/Polaris",
            "passive_telemetry": False,
        }
        if name:
            metadata["device_name"] = name
        if uuid_hit:
            metadata["adv_service_seen"] = True
        if family:
            metadata["family"] = family
            metadata["model"] = model
        if suffix:
            metadata["unit_suffix"] = suffix

        if suffix:
            id_basis = f"zodiac_iaqualink:{suffix}"
        else:
            id_basis = f"zodiac_iaqualink:mac:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="zodiac_iaqualink",
            beacon_type="zodiac_iaqualink",
            device_class=device_class,
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
