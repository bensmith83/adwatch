"""SimpliSafe Home Security plugin (base station + smart lock).

Per apk-ble-hunting/reports/simplisafe-mobile_passive.md:

  - SIG company ID ``0x06B1`` (1713 — SimpliSafe Inc.)
  - Base station service UUIDs ``0x0D18`` and ``0x00CC`` (firmware-vintage
    dependent)
  - Smart Lock application service UUID
    ``26526EEA-C96A-45D0-854E-3BB05C450B56``
  - Smart Lock DFU/bootloader uses the industry-wide Nordic DFU UUID
    ``0xFE59`` — gated to require the SimpliSafe CID *also* be present so
    we don't steal sightings from every other Nordic-DFU bootloader.

Manufacturer-data layout (SimpliSafe is privacy-aware: literal serial is
NOT broadcast, only a SHA-256 fragment):

  - [0..3] serial-tag    = ``SHA-256(serial)[-8:]`` (the *last* hex byte
                           of the serial, hashed)
  - [4..7] extended-serial-tag = secondary hash used to detect hardware
                                 swaps
  - [8..]  unparsed Java-side (mbedTLS/native lib may decode firmware
           version + capability flags — Stage 6a)
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


SIMPLISAFE_CID = 0x06B1  # 1713
BASESTATION_UUIDS = ["0d18", "00cc"]
LOCK_APP_UUID = "26526eea-c96a-45d0-854e-3bb05c450b56"
NORDIC_DFU_UUID = "0000fe59-0000-1000-8000-00805f9b34fb"


@register_parser(
    name="simplisafe",
    company_id=SIMPLISAFE_CID,
    service_uuid=BASESTATION_UUIDS + [LOCK_APP_UUID],
    description="SimpliSafe base station + smart lock advertisements",
    version="1.0.0",
    core=False,
)
class SimpliSafeParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        cid_hit = raw.company_id == SIMPLISAFE_CID

        normalized = [u.lower() for u in (raw.service_uuids or [])]
        base_uuid_hit = any(
            u == short or u.endswith(f"0000{short}-0000-1000-8000-00805f9b34fb")
            for u in normalized for short in BASESTATION_UUIDS
        )
        lock_app_hit = LOCK_APP_UUID in normalized
        dfu_hit = NORDIC_DFU_UUID in normalized

        # DFU UUID alone is industry-wide; only treat as SimpliSafe lock-DFU
        # when the SimpliSafe CID is also present in the same advertisement.
        ss_dfu_hit = dfu_hit and cid_hit

        if not (cid_hit or base_uuid_hit or lock_app_hit or ss_dfu_hit):
            return None

        metadata: dict = {"vendor": "SimpliSafe"}

        if base_uuid_hit:
            metadata["product_class"] = "base_station"
        elif lock_app_hit:
            metadata["product_class"] = "smart_lock"
            metadata["mode"] = "application"
        elif ss_dfu_hit:
            metadata["product_class"] = "smart_lock"
            metadata["mode"] = "dfu"
        else:
            metadata["product_class"] = "unknown"

        serial_tag: str | None = None
        if cid_hit:
            payload = raw.manufacturer_payload or b""
            if len(payload) >= 4:
                serial_tag = payload[0:4].hex()
                metadata["serial_tag_hex"] = serial_tag
            if len(payload) >= 8:
                metadata["extended_serial_tag_hex"] = payload[4:8].hex()

        if serial_tag:
            id_basis = f"simplisafe:{serial_tag}"
        else:
            id_basis = f"simplisafe:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="simplisafe",
            beacon_type="simplisafe",
            device_class="security",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
