"""Tuya / Smart Life BLE advertisement plugin.

Covers two unrelated Tuya shapes:

* **CID 0x07D0** — the Tuya BLE protocol header (version, flags, product id).
* **Service data 0xFD50** — the Tuya "pink" FlowerCare plant-sensor clone,
  a fixed 9-byte broadcast carrying every reading at once.  Layout verified
  against ``reports/watchflower_passive.md`` (WatchFlower is open source;
  ``src/src/devices/device_flowercare_tuya.cpp:120-179``):

  ===  ===  ==============================================================
  off  len  field
  ===  ===  ==============================================================
  0    1    soil moisture, %
  1    2    temperature, int16 **big-endian**, /10 °C
  3    3    luminosity, uint24 little-endian, lux
  6    1    battery, %
  7    2    soil conductivity, uint16 **big-endian**, µS/cm
  ===  ===  ==============================================================

  The big-endian temperature and conductivity are unusual for BLE and are
  taken straight from the WatchFlower source, which requires the payload to
  be exactly 9 bytes long.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser, _normalize_uuid

TUYA_COMPANY_ID = 0x07D0

# Tuya plant sensor ("TY") broadcast service.
TUYA_FLOWERCARE_UUID = "fd50"
_TUYA_FLOWERCARE_UUID_FULL = _normalize_uuid(TUYA_FLOWERCARE_UUID)
TUYA_FLOWERCARE_LEN = 9

# Cheap Tuya-clone WiFi smart devices (plugs, bulbs) advertise this exact
# name shape in pairing mode. They typically don't carry the SIG-correct
# Tuya CID — name is the only signal. Locked to uppercase/digit pairs to
# stay narrow.
_TUYA_CLONE_NAME_RE = re.compile(r"^Smart\.[A-Z0-9]{2}\.WIFI$")

# WatchFlower discovers the Tuya plant sensor by the exact local name "TY".
_TUYA_NAME_PATTERN = r"^(Smart\.[A-Z0-9]{2}\.WIFI|TY)$"


@register_parser(
    name="tuya",
    company_id=TUYA_COMPANY_ID,
    service_uuid=TUYA_FLOWERCARE_UUID,
    local_name_pattern=_TUYA_NAME_PATTERN,
    description="Tuya / Smart Life BLE advertisements (incl. FlowerCare clone and cheap-clone pairing-mode name)",
    version="1.2.0",
    core=False,
)
class TuyaParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        local_name = getattr(raw, "local_name", None) or ""

        # CID path — full Tuya BLE protocol decode.
        if raw.manufacturer_data and len(raw.manufacturer_data) >= 4:
            company_id = int.from_bytes(raw.manufacturer_data[:2], "little")
            if company_id == TUYA_COMPANY_ID:
                payload = raw.manufacturer_data[2:]
                protocol_version = payload[0]
                flags = payload[1]
                pairing = bool(flags & 0x01)

                metadata: dict = {
                    "protocol_version": protocol_version,
                    "flags": flags,
                    "pairing": pairing,
                }

                if len(payload) > 2:
                    metadata["product_id_hex"] = payload[2:].hex()

                if local_name:
                    metadata["local_name"] = local_name

                id_hash = hashlib.sha256(
                    f"{raw.mac_address}:tuya".encode()
                ).hexdigest()[:16]

                return ParseResult(
                    parser_name="tuya",
                    beacon_type="tuya",
                    device_class="smart_home",
                    identifier_hash=id_hash,
                    raw_payload_hex=payload.hex(),
                    metadata=metadata,
                )

        # Tuya FlowerCare clone — fixed 9-byte 0xFD50 service data.
        flower = self._flowercare_payload(raw)
        if flower is not None:
            return self._parse_flowercare(raw, flower)

        # Cheap-clone name-only path — pairing-mode `Smart.<XX>.WIFI`.
        if _TUYA_CLONE_NAME_RE.match(local_name):
            id_hash = hashlib.sha256(
                f"{raw.mac_address}:tuya".encode()
            ).hexdigest()[:16]
            return ParseResult(
                parser_name="tuya",
                beacon_type="tuya",
                device_class="smart_home",
                identifier_hash=id_hash,
                raw_payload_hex="",
                metadata={
                    "local_name": local_name,
                    "match_source": "name_regex",
                    "pairing_mode_clone": True,
                    "pairing": True,
                },
            )

        return None

    @staticmethod
    def _flowercare_payload(raw: RawAdvertisement) -> bytes | None:
        """Return the 0xFD50 service data iff it is exactly 9 bytes long."""
        for key, value in (raw.service_data or {}).items():
            if _normalize_uuid(key) != _TUYA_FLOWERCARE_UUID_FULL:
                continue
            if len(value) == TUYA_FLOWERCARE_LEN:
                return value
        return None

    def _parse_flowercare(self, raw: RawAdvertisement, data: bytes) -> ParseResult:
        metadata: dict = {
            "soil_moisture": data[0],
            # Big-endian: data[2] + (data[1] << 8)
            "temperature_c": int.from_bytes(data[1:3], "big", signed=True) / 10.0,
            "luminosity": int.from_bytes(data[3:6], "little"),
            "battery": data[6],
            # Big-endian: data[8] + (data[7] << 8)
            "soil_conductivity": int.from_bytes(data[7:9], "big"),
        }
        if raw.local_name:
            metadata["local_name"] = raw.local_name

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:tuya".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="tuya",
            beacon_type="tuya_flowercare",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
