"""Toyota PAAK (Phone-as-a-Key) / Denso DKLib advertisement parser.

Per apk-ble-hunting/reports/toyota-oneapp_passive.md.

A phone running the Toyota App with a digital key enabled emits **two**
parallel advertisements, both carrying the Denso DKLib UUID
``DBC6B52C-810F-40E1-B316-BB5D94C275F7``:

1. **Connectable peripheral** — 128-bit service UUID + local name. The app
   rewrites the adapter name to the literal ``"Passive"`` in steady state
   (``Constants.java:61``), or to an 8-hex-char ``vehicleId`` substring during
   the vehicle-registration handshake (``RegisterVehicleCtl.java:457``).
2. **Non-connectable iBeacon** (emitted through AltBeacon) — Apple company ID
   ``0x004C``, ``02 15`` prefix, the same Denso UUID as the proximity UUID,
   and a Major/Minor pair issued by Toyota's cloud at key download. The pair
   is stable for the life of the digital key, so it is a per-(vehicle, key)
   fingerprint that survives BLE MAC rotation — that is what we hash.

Registration note: like ``volvo.py``, we register on the Apple company ID so
every iBeacon routes through here; the Denso proximity UUID is the real
signal and ``parse()`` returns ``None`` for any other iBeacon.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import _normalize_uuid, register_parser


TOYOTA_DENSO_UUID = "dbc6b52c-810f-40e1-b316-bb5d94c275f7"
TOYOTA_DENSO_UUID_HEX = TOYOTA_DENSO_UUID.replace("-", "")
_TOYOTA_UUID_NORMALIZED = _normalize_uuid(TOYOTA_DENSO_UUID)

APPLE_COMPANY_ID = 0x004C

# Adapter name the app sets in steady state (Constants.java:61).
STEADY_STATE_NAME = "Passive"

# Registration-handshake name: an 8-hex-char vehicleId substring.
_VEHICLE_ID_RE = re.compile(r"^[0-9a-fA-F]{8}$")


@register_parser(
    name="toyota_paak",
    company_id=APPLE_COMPANY_ID,
    service_uuid=TOYOTA_DENSO_UUID,
    description="Toyota PAAK digital key (Denso DKLib) phone/vehicle advertisements",
    version="1.0.0",
    core=False,
)
class ToyotaPaakParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        metadata: dict = {"vendor": "Toyota", "stack": "Denso DKLib"}

        major = minor = None
        payload = raw.manufacturer_payload
        is_ibeacon = (
            raw.manufacturer_data is not None
            and len(raw.manufacturer_data) >= 2
            and int.from_bytes(raw.manufacturer_data[:2], "little") == APPLE_COMPANY_ID
            and payload is not None
            and len(payload) >= 23
            and payload[0] == 0x02
            and payload[1] == 0x15
            and payload[2:18].hex() == TOYOTA_DENSO_UUID_HEX
        )

        has_uuid = any(
            _normalize_uuid(u) == _TOYOTA_UUID_NORMALIZED
            for u in (raw.service_uuids or [])
        )

        if not (is_ibeacon or has_uuid):
            return None

        if is_ibeacon:
            major = int.from_bytes(payload[18:20], "big")
            minor = int.from_bytes(payload[20:22], "big")
            tx = payload[22]
            metadata["advert_role"] = "ibeacon_wake"
            metadata["proximity_uuid"] = TOYOTA_DENSO_UUID
            metadata["major"] = major
            metadata["minor"] = minor
            metadata["key_fingerprint"] = f"{major:04x}{minor:04x}"
            metadata["tx_power"] = tx - 256 if tx >= 128 else tx
        else:
            metadata["advert_role"] = "connectable_peripheral"
            metadata["service_uuid"] = TOYOTA_DENSO_UUID

        name = raw.local_name or ""
        vehicle_id = None
        if name:
            metadata["device_name"] = name
            if name == STEADY_STATE_NAME:
                metadata["name_state"] = "steady_state"
            elif _VEHICLE_ID_RE.match(name):
                metadata["name_state"] = "registration"
                vehicle_id = name
                metadata["vehicle_id_fragment"] = name
            else:
                metadata["name_state"] = "other"

        if major is not None:
            id_basis = f"toyota_paak:{major:04x}{minor:04x}"
        elif vehicle_id is not None:
            id_basis = f"toyota_paak:vid:{vehicle_id}"
        else:
            id_basis = f"toyota_paak:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="toyota_paak",
            beacon_type="toyota_paak",
            device_class="vehicle",
            identifier_hash=id_hash,
            raw_payload_hex=(payload.hex() if is_ibeacon and payload else ""),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
