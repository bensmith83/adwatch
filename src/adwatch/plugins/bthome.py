"""BTHome v1/v2 BLE advertisement parser.

Object table and the v1 framing were cross-checked against
``reports/watchflower_passive.md`` — WatchFlower is open source, so its
``src/src/device_sensor_advertisement.cpp:561-858`` is ground truth rather
than inference.

* **v2** rides on service UUID ``0xFCD2``.  Byte 0 is a device-info byte:
  bit 0 = encrypted, bits 5-7 = version.  Objects follow with no per-object
  prefix.
* **v1** rides on ``0x181C`` (plain) or ``0x181E`` (encrypted).  There is no
  device-info byte; each object is preceded by one prefix byte whose low 5
  bits are the length and whose top 3 bits are the format.  WatchFlower reads
  that byte and ignores both fields, taking the length from its own object
  table — this parser does the same, so a wrong prefix cannot desynchronise
  the loop.

Encrypted BTHome (``0x181E``, or the v2 info-byte bit 0) is detected and
rejected rather than decoded.
"""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser, _normalize_uuid

BTHOME_UUID = "fcd2"
BTHOME_V1_UUID = "181c"
BTHOME_V1_ENCRYPTED_UUID = "181e"
BTHOME_SERVICE_UUIDS = (BTHOME_UUID, BTHOME_V1_UUID, BTHOME_V1_ENCRYPTED_UUID)

_UUID_LOOKUP = {
    _normalize_uuid(BTHOME_UUID): (2, False),
    _normalize_uuid(BTHOME_V1_UUID): (1, False),
    _normalize_uuid(BTHOME_V1_ENCRYPTED_UUID): (1, True),
}

BUTTON_EVENT_MAP = {
    0x00: "none",
    0x01: "press",
    0x02: "double_press",
    0x03: "triple_press",
    0x04: "long_press",
    0x05: "long_double_press",
    0x06: "long_triple_press",
    0x80: "hold_press",
}

# Object ID -> (name, length_bytes, format, scale)
# format: 'u' = unsigned, 's' = signed
OBJECT_DEFS = {
    0x00: ("packet_id", 1, "u", 1),
    0x01: ("battery", 1, "u", 1),
    0x02: ("temperature", 2, "s", 0.01),
    0x03: ("humidity", 2, "u", 0.01),
    0x04: ("pressure", 3, "u", 0.01),
    0x05: ("illuminance", 3, "u", 0.01),
    0x06: ("mass_kg", 2, "u", 0.01),
    0x07: ("mass_lb", 2, "u", 0.01),
    0x08: ("dew_point", 2, "s", 0.01),
    0x09: ("count", 1, "u", 1),
    0x0A: ("energy", 3, "u", 0.001),
    0x0B: ("power", 3, "u", 0.01),
    0x0C: ("voltage", 2, "u", 0.001),
    0x0D: ("pm25", 2, "u", 1),
    0x0E: ("pm10", 2, "u", 1),
    0x0F: ("generic_boolean", 1, "u", 1),
    0x10: ("power_binary", 1, "u", 1),
    0x11: ("opening", 1, "u", 1),
    0x12: ("co2", 2, "u", 1),
    0x13: ("tvoc", 2, "u", 1),
    0x14: ("moisture", 2, "u", 0.01),
    0x15: ("battery_low", 1, "u", 1),
    0x16: ("battery_charging", 1, "u", 1),
    0x17: ("co_detected", 1, "u", 1),
    0x1A: ("door", 1, "u", 1),
    0x1C: ("gas", 1, "u", 1),
    0x1D: ("heat", 1, "u", 1),
    0x1E: ("light", 1, "u", 1),
    0x1F: ("lock", 1, "u", 1),
    0x20: ("moisture_binary", 1, "u", 1),
    0x21: ("motion", 1, "u", 1),
    0x22: ("moving", 1, "u", 1),
    0x23: ("occupancy", 1, "u", 1),
    0x2D: ("window", 1, "u", 1),
    0x2E: ("humidity", 1, "u", 1),
    0x2F: ("moisture", 1, "u", 1),
    0x3A: ("button_event", 1, "u", 1),
    0x3C: ("dimmer_event", 2, "u", 1),
    0x45: ("temperature_01", 2, "s", 0.1),
    0x46: ("uv_index", 1, "u", 0.1),
}


@register_parser(
    name="bthome",
    service_uuid=BTHOME_SERVICE_UUIDS,
    description="BTHome v1/v2 sensor advertisements",
    version="1.1.0",
    core=False,
)
class BTHomeParser:
    @staticmethod
    def _find_payload(raw: RawAdvertisement):
        """Return (payload, version, uuid_is_encrypted) for the first BTHome
        service-data entry, in FCD2 > 181C > 181E order."""
        if not raw.service_data:
            return None
        normalized = {}
        for key, value in raw.service_data.items():
            normalized.setdefault(_normalize_uuid(key), value)
        for uuid, (version, enc) in _UUID_LOOKUP.items():
            if uuid in normalized:
                return normalized[uuid], version, enc
        return None

    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        found = self._find_payload(raw)
        if found is None:
            return None
        data, version, uuid_is_encrypted = found

        if len(data) < 2:
            return None

        if version == 2:
            device_info = data[0]
            version = (device_info >> 5) & 0x07
            if version != 2:
                return None
            if device_info & 0x01:
                return None
            offset = 1
        else:
            # v1: encryption is signalled by the service UUID itself.
            if uuid_is_encrypted:
                return None
            offset = 0

        metadata: dict[str, str | int | float | bool] = {"bthome_version": version}

        while offset < len(data):
            if version == 1:
                # Prefix byte: length = b & 0x1F, format = b >> 5. Both are
                # deliberately ignored (WatchFlower Q_UNUSEDs them).
                offset += 1
                if offset >= len(data):
                    break
            obj_id = data[offset]
            offset += 1

            if obj_id not in OBJECT_DEFS:
                break

            name, length, fmt, scale = OBJECT_DEFS[obj_id]

            if offset + length > len(data):
                break

            obj_bytes = data[offset:offset + length]
            offset += length

            if length == 1:
                value = obj_bytes[0] if fmt == "u" else struct.unpack("<b", obj_bytes)[0]
            elif length == 2:
                value = struct.unpack("<H" if fmt == "u" else "<h", obj_bytes)[0]
            elif length == 3:
                value = int.from_bytes(obj_bytes, "little")
                if fmt == "s" and value >= 0x800000:
                    value -= 0x1000000

            if name == "button_event":
                value = BUTTON_EVENT_MAP.get(value, value)
            elif name == "dimmer_event":
                steps = obj_bytes[0]
                direction = "clockwise" if obj_bytes[1] == 0 else "counter_clockwise"
                metadata[name] = {"steps": steps, "direction": direction}
                continue

            metadata[name] = value * scale if scale != 1 else value

        # bthome_version alone is not a reading.
        if len(metadata) <= 1:
            return None

        id_hash = hashlib.sha256(raw.mac_address.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="bthome",
            beacon_type="bthome",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata=metadata,
        )
