"""Moto Tag (Motorola FMDN tracker) owner-advert plugin.

Per apk-ble-hunting/reports/motorola-tag_passive.md.

The tag has two advert faces:
  - ``0xFEAA`` Eddystone/FMDN network beacon (rotating EID, decoded by GMS).
    Generic across vendors — NOT claimed here (``eddystone`` owns it); only
    reported as ``fmdn_frame_seen`` corroboration.
  - ``0xFC7C`` service data, exactly 1 byte, bit-packed status the app
    decodes (``L4/C0247g.java``):
      bits 7-6 state, 5-4 sub-state, 3 UWB capability, 2-1 category,
      0 mode (0=FMD, 1=SM / SmartConnect).

Service data comes from ``getServiceData`` so there is no CID offset shift.
MACs are randomized — identity is per-MAC only.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


MOTO_TAG_SERVICE_UUID = "fc7c"
_FULL_UUID = "0000fc7c-0000-1000-8000-00805f9b34fb"
_FEAA_KEYS = ("feaa", "0000feaa-0000-1000-8000-00805f9b34fb")

MODES = {0: "FMD", 1: "SM"}


@register_parser(
    name="moto_tag",
    service_uuid=MOTO_TAG_SERVICE_UUID,
    description="Motorola Moto Tag (0xFC7C owner status advert)",
    version="1.0.0",
    core=False,
)
class MotoTagParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        sd = raw.service_data or {}
        data = sd.get(MOTO_TAG_SERVICE_UUID)
        if data is None:
            data = sd.get(_FULL_UUID)
        if data is None or len(data) != 1:
            return None

        b = data[0]
        mode_code = b & 0x01
        metadata: dict = {
            "vendor": "Motorola",
            "product": "Moto Tag",
            "status_byte": b,
            "state_code": (b >> 6) & 0x03,
            "sub_state": (b >> 4) & 0x03,
            "uwb_capable": bool(b & 0x08),
            "category_code": (b >> 1) & 0x03,
            "mode_code": mode_code,
            "mode": MODES[mode_code],
            "fmdn_frame_seen": any(k in sd for k in _FEAA_KEYS),
        }

        id_hash = hashlib.sha256(f"moto_tag:{raw.mac_address}".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="moto_tag",
            beacon_type="moto_tag",
            device_class="tracker",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
