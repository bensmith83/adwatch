"""Xiaomi MiBeacon (service data 0xFE95) advertisement parser.

Frame control bits, the object-ID table and the product-ID table were
cross-checked against ``reports/watchflower_passive.md``.  WatchFlower is
open-source Qt/C++ (``src/src/device_sensor_advertisement.cpp:139-396``), so it
is ground truth rather than inference.

Corrections that came out of that audit (all previously wrong here):

* **Encryption is frame-control bit 3**, not bit 7 — bit 7 is ``isMeshed``.
  Treating mesh frames as encrypted silently dropped them.
* **0x1007 is luminosity** (uint24 LE, lux); the door event is ``0x0007`` in
  the short-ID space.  The two were swapped.
* **Soil moisture / conductivity are 0x1008 / 0x1009**, not 0x0008 / 0x0009.
* **0x1002 is the sleep state**, not "no motion".
* **Gas state is 0x1016**, not 0x1018.
* The capability byte's bit 5 (``hasIO``) is followed by a **2-byte** IO
  capability field, which has to be skipped or the object header is read at
  the wrong offset.

Frame layout::

    0    2  frame control   uint16 LE
    2    2  product ID      uint16 LE  (selects the device model)
    4    1  frame counter   uint8      (increments per advertisement)
    5    6  MAC (reversed)  present only when frame-control bit 4 is set
    ...  1  capability      present only when frame-control bit 5 is set
    ...  2  IO capability   present only when capability bit 5 is set
    ...  2  object type     uint16 LE  (frame-control bit 6)
    ...  1  object length   uint8
    ...  N  object data

Exactly one measurement object is sent per frame, so a scanner has to
accumulate frames to see everything a device reports.

``reports/yeelight-cherry_passive.md`` (``MiotPacketParser`` in
``com.yeelight.cherry``) decodes the same header independently and agrees with
WatchFlower on every bit index.  It adds the byte-1 detail used here: bit 0
``registered``, bit 1 ``bindingCfm``, bits 2-3 ``authMode``
(0=RC4, 1=SecureAuth, 2=StandardAuth), bits 4-7 ``version`` — which settles
the WatchFlower table's ``[13:15]`` wording as bits 12-15 of the 16-bit frame
control.  It also documents the capability sub-fields, the 2-byte combo key,
and the version-5 event re-ordering, all implemented below.

Known divergences, left as-is deliberately:

* The report gives formaldehyde (0x1010) as ``/10 µg/m³``; this parser keeps
  ``/100`` (mg/m³), the interpretation used by Xiaomi's own JQJCY01YM tooling.
* The Yeelight report has a padding byte after the 2-byte IO capability field;
  WatchFlower does not.  WatchFlower is the stated ground truth here, so the
  IO capability consumes 2 bytes.
* The v>=5 event ID is a single byte drawn from an ID space neither report
  documents, so those events are surfaced raw rather than decoded.
"""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

MIBEACON_UUID = "fe95"

# --- Frame control bits ---
FC_ENCRYPTED = 3
FC_HAS_MAC = 4
FC_HAS_CAPABILITY = 5
FC_HAS_OBJECT = 6
FC_MESH = 7
FC_REGISTERED = 8
# WatchFlower calls bit 9 isSolicited; MiotPacketParser calls it bindingCfm.
FC_SOLICITED = 9

AUTH_MODES = {0: "rc4", 1: "secure_auth", 2: "standard_auth"}

# withCapability && bindable == 3 && version >= 3 inserts a 2-byte combo key.
COMBO_KEY_BINDABLE = 3
COMBO_KEY_MIN_VERSION = 3

# Version 5 re-orders the event header to length(1) + id(1).
EVENT_V5_MIN_VERSION = 5

# --- Object IDs ---
# Short-ID space (Xiaomi event objects).
OBJECT_MOTION_ILLUMINANCE = 0x0003
OBJECT_DOOR_EVENT = 0x0007
OBJECT_BATTERY_LOW = 0x000A
OBJECT_DOOR_WINDOW = 0x000F
# 0x10xx measurement space.
OBJECT_MOTION = 0x1001
OBJECT_SLEEP_STATE = 0x1002
OBJECT_RSSI = 0x1003
OBJECT_TEMP = 0x1004
OBJECT_BUTTON = 0x1005
OBJECT_HUMIDITY = 0x1006
OBJECT_ILLUMINANCE = 0x1007
OBJECT_SOIL_MOISTURE = 0x1008
OBJECT_SOIL_CONDUCTIVITY = 0x1009
OBJECT_BATTERY = 0x100A
OBJECT_TEMP_HUMIDITY = 0x100D
OBJECT_LOCK_STATE = 0x100E
OBJECT_DOOR_STATE = 0x100F
OBJECT_FORMALDEHYDE = 0x1010
OBJECT_BIND_STATE = 0x1011
OBJECT_SWITCH_EVENT = 0x1012
OBJECT_CONSUMABLES = 0x1013
OBJECT_FLOOD = 0x1014
OBJECT_SMOKE = 0x1015
OBJECT_GAS = 0x1016

# Product ID (bytes 2-3) -> model, for the families WatchFlower supports.
PRODUCT_IDS = {
    0x0098: "HHCCJCY01",     # Flower care
    0x03BC: "HHCCJCY09",     # Grow care garden / GCLS002
    0x015D: "HHCCPOT002",    # ropot
    0x01AA: "LYWSDCGQ",      # MJ_HT_V1
    0x045B: "LYWSD02",
    0x06D3: "MHO-C303",
    0x0347: "CGG1",
    0x066F: "CGDK2",
    0x02DF: "JQJCY01YM",
}


@register_parser(
    name="mibeacon",
    service_uuid=MIBEACON_UUID,
    description="Xiaomi MiBeacon",
    version="1.1.0",
    core=False,
)
class MiBeaconParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.service_data or MIBEACON_UUID not in raw.service_data:
            return None

        data = raw.service_data[MIBEACON_UUID]
        if len(data) < 5:
            return None

        try:
            return self._parse_inner(raw, data)
        except struct.error:
            return None

    def _parse_inner(self, raw: RawAdvertisement, data: bytes) -> ParseResult | None:
        frame_control, device_type, frame_counter = struct.unpack_from("<HHB", data, 0)
        offset = 5

        has_mac = bool(frame_control & (1 << FC_HAS_MAC))
        has_capability = bool(frame_control & (1 << FC_HAS_CAPABILITY))
        has_object = bool(frame_control & (1 << FC_HAS_OBJECT))
        encrypted = bool(frame_control & (1 << FC_ENCRYPTED))

        if encrypted:
            return None

        auth_mode = (frame_control >> 10) & 0x03
        version = (frame_control >> 12) & 0x0F
        is_registered = bool(frame_control & (1 << FC_REGISTERED))
        binding_cfm = bool(frame_control & (1 << FC_SOLICITED))

        metadata: dict[str, str | int | float | bool] = {
            "device_type": device_type,
            "frame_counter": frame_counter,
            "is_mesh": bool(frame_control & (1 << FC_MESH)),
            "is_registered": is_registered,
            "is_solicited": binding_cfm,
            "binding_confirmation": binding_cfm,
            "auth_mode": auth_mode,
            "auth_mode_name": AUTH_MODES.get(auth_mode, "unknown"),
            "protocol_version": version,
        }

        model = PRODUCT_IDS.get(device_type)
        if model:
            metadata["device_model"] = model

        mac_str = None
        if has_mac:
            if offset + 6 > len(data):
                return None
            mac_bytes = data[offset:offset + 6]
            mac_str = ":".join(f"{b:02X}" for b in reversed(mac_bytes))
            metadata["mac"] = mac_str
            offset += 6

        if has_capability:
            if offset >= len(data):
                return None
            capability = data[offset]
            offset += 1
            connectable = bool(capability & 0x01)
            bindable = (capability >> 3) & 0x03
            metadata["capability"] = capability
            metadata["connectable"] = connectable
            metadata["centralable"] = bool(capability & 0x02)
            metadata["encryptable"] = bool(capability & 0x04)
            metadata["bindable"] = bindable
            # A factory-reset Xiaomi-ecosystem device advertises itself as
            # bindable and connectable but not yet registered.
            metadata["unprovisioned"] = connectable and not is_registered

            if bindable == COMBO_KEY_BINDABLE and version >= COMBO_KEY_MIN_VERSION:
                if offset + 2 > len(data):
                    return None
                metadata["combo_key_hex"] = data[offset:offset + 2].hex()
                offset += 2

            if capability & 0x20:
                # Capability bit 5 (ioCapabilityable) adds a 2-byte IO field.
                metadata["has_io"] = True
                if offset + 2 > len(data):
                    return None
                metadata["io_capability"] = struct.unpack_from("<H", data, offset)[0]
                offset += 2

        if has_object:
            if version >= EVENT_V5_MIN_VERSION:
                # v5+: length(1) + id(1) + data.  The 1-byte ID space is not
                # documented, so the payload is surfaced but not decoded.
                if offset + 2 <= len(data):
                    obj_len = data[offset]
                    object_id = data[offset + 1]
                    offset += 2
                    metadata["object_id"] = object_id
                    metadata["object_data_hex"] = data[offset:offset + obj_len].hex()
            elif offset + 3 <= len(data):
                object_id, obj_len = struct.unpack_from("<HB", data, offset)
                offset += 3
                obj_data = data[offset:offset + obj_len]
                metadata["object_id"] = object_id
                self._decode_object(metadata, object_id, obj_data)

        identity_mac = mac_str or raw.mac_address
        id_hash = hashlib.sha256(identity_mac.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="mibeacon",
            beacon_type="mibeacon",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata=metadata,
        )

    @staticmethod
    def _decode_object(metadata: dict, object_id: int, obj_data: bytes) -> None:
        if object_id == OBJECT_MOTION_ILLUMINANCE and len(obj_data) >= 4:
            metadata["illuminance"] = struct.unpack_from("<I", obj_data, 0)[0]
        elif object_id == OBJECT_DOOR_EVENT and len(obj_data) >= 1:
            metadata["door_event"] = "closed" if obj_data[0] else "open"
        elif object_id == OBJECT_BATTERY_LOW and len(obj_data) >= 1:
            metadata["battery"] = obj_data[0]
        elif object_id == OBJECT_DOOR_WINDOW and len(obj_data) >= 1:
            metadata["door_window"] = "closed" if obj_data[0] else "open"
        elif object_id == OBJECT_MOTION:
            metadata["motion"] = True
        elif object_id == OBJECT_SLEEP_STATE and len(obj_data) >= 1:
            metadata["sleep_state"] = obj_data[0]
        elif object_id == OBJECT_RSSI and len(obj_data) >= 1:
            metadata["reported_rssi"] = obj_data[0]
        elif object_id == OBJECT_TEMP and len(obj_data) >= 2:
            metadata["temperature"] = struct.unpack_from("<h", obj_data, 0)[0] / 10.0
        elif object_id == OBJECT_BUTTON and len(obj_data) >= 2:
            metadata["button_event_type"] = obj_data[0]
            metadata["button_count"] = obj_data[1]
        elif object_id == OBJECT_HUMIDITY and len(obj_data) >= 2:
            metadata["humidity"] = struct.unpack_from("<h", obj_data, 0)[0] / 10.0
        elif object_id == OBJECT_ILLUMINANCE and len(obj_data) >= 3:
            metadata["illuminance"] = int.from_bytes(obj_data[:3], "little")
        elif object_id == OBJECT_SOIL_MOISTURE and obj_data:
            # WatchFlower reads a uint16; real HHCC frames often carry 1 byte.
            metadata["soil_moisture"] = (
                struct.unpack_from("<H", obj_data, 0)[0]
                if len(obj_data) >= 2 else obj_data[0]
            )
        elif object_id == OBJECT_SOIL_CONDUCTIVITY and len(obj_data) >= 2:
            metadata["soil_conductivity"] = struct.unpack_from("<H", obj_data, 0)[0]
        elif object_id == OBJECT_BATTERY and len(obj_data) >= 1:
            metadata["battery"] = obj_data[0]
        elif object_id == OBJECT_TEMP_HUMIDITY and len(obj_data) >= 4:
            metadata["temperature"] = struct.unpack_from("<h", obj_data, 0)[0] / 10.0
            metadata["humidity"] = struct.unpack_from("<H", obj_data, 2)[0] / 10.0
        elif object_id == OBJECT_LOCK_STATE and len(obj_data) >= 1:
            metadata["lock_state"] = obj_data[0]
        elif object_id == OBJECT_DOOR_STATE and len(obj_data) >= 1:
            metadata["door_state"] = obj_data[0]
        elif object_id == OBJECT_FORMALDEHYDE and len(obj_data) >= 2:
            metadata["formaldehyde"] = struct.unpack_from("<H", obj_data, 0)[0] / 100.0
        elif object_id == OBJECT_BIND_STATE and len(obj_data) >= 1:
            metadata["bind_state"] = obj_data[0]
        elif object_id == OBJECT_SWITCH_EVENT and len(obj_data) >= 1:
            metadata["switch_event"] = obj_data[0]
        elif object_id == OBJECT_CONSUMABLES and len(obj_data) >= 1:
            metadata["consumables"] = obj_data[0]
        elif object_id == OBJECT_FLOOD and len(obj_data) >= 1:
            metadata["flood"] = "wet" if obj_data[0] else "dry"
        elif object_id == OBJECT_SMOKE and len(obj_data) >= 1:
            metadata["smoke"] = "smoke" if obj_data[0] else "clear"
        elif object_id == OBJECT_GAS and len(obj_data) >= 1:
            metadata["gas"] = "gas" if obj_data[0] else "clear"
