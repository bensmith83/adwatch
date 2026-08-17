"""Ultimate Ears (Logitech) BOOM / MEGABOOM / WONDERBOOM speaker plugin.

Per apk-ble-hunting/reports/ue-boom_passive.md (com.logitech.ueboom).

UE speakers broadcast an unusually rich, unencrypted manufacturer-data payload
alongside the Logitech 16-bit service UUID ``0xFE61``. The report documents
offsets relative to the FULL scan record::

    off 0  : 02 01 xx        Flags AD (0x12 = CPP, 0x06 = legacy ADK2)
    off 3  : 02 08 00        Shortened Local Name AD, zero length
    off 6  : 03 03 61 FE     16-bit service UUID 0xFE61
    off 10 : 10 FF           Manufacturer Specific Data AD header
    off 12 : DA 01           Logitech SIG company ID 0x01DA (little-endian)
    off 14 : ... 13 bytes    vendor payload

``RawAdvertisement.manufacturer_payload`` strips the company ID, so payload
index 0 == record offset 14. That lines up exactly with the report's CPP field
table and its "Scanner Implementation Notes" (battery at record byte 14,
status byte at record byte 18 == payload[4]).

Two payload shapes are decoded:

* **Wasp** — identified by the report's validation rule PID ``{03, 0D}`` at
  record offset 14-15 (payload[0:2]). Carries audio-source / playing / powered
  flags and a 2-bit group id in the status byte at record offset 23
  (payload[9]).
* **CPP / legacy ADK2** — battery + power bit, volume, event bitmask, a
  multi-flag status byte, an XUP/PartyUp extra-flags byte, the 6-byte
  broadcaster MAC and a name-revision nibble.

The speaker's own MAC (record offsets 44-49) sits outside the manufacturer
data AD and is therefore not visible here; the report notes UE speakers do not
randomize their BLE address, so identity hashes off the observed MAC.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import _normalize_uuid, register_parser


UE_SERVICE_UUID = "fe61"
LOGITECH_COMPANY_ID = 0x01DA

_UE_SERVICE_UUID_NORM = _normalize_uuid(UE_SERVICE_UUID)

# Minimum vendor payload length (record offsets 14..26).
_PAYLOAD_LEN = 13

# Wasp validation: PID {0x03, 0x0D} at record offset 14-15.
_WASP_PID = 0x030D

# BLEPid.java product codes (stored big-endian in the advertisement).
PRODUCT_IDS = {
    0x0300: "BOOM / MAXIMUS",
    0x0301: "MEGABOOM (MANHATTAN)",
    0x0302: "WONDERBOOM (BROOKLYN)",
    0x0306: "MOTORCITY",
    0x0307: "MULBERRIES",
    0x030D: "WASP",
}

# BroadcastReceiverStatus.java — 3-bit field at bits [7:5] of the extra-flags
# byte. The enum defines codes 8/9 too, but only 0-7 are reachable in 3 bits.
BROADCAST_RECEIVER_STATUS = {
    0: "POWER_OFF",
    1: "NO_STREAMING_NOT_CONNECTED",
    2: "CONNECTED_NO_STREAMING",
    3: "STREAMING_A2DP",
    4: "STREAMING_AUX_NOT_CONNECTED",
    5: "STREAMING_AUX",
    6: "LOCAL_HFP",
    7: "PLAYING_ANOTHER_BROADCAST",
}


def _mac(raw: bytes) -> str:
    return ":".join(f"{b:02x}" for b in raw)


@register_parser(
    name="ue_boom",
    company_id=LOGITECH_COMPANY_ID,
    service_uuid=UE_SERVICE_UUID,
    description="Ultimate Ears (Logitech) BOOM / MEGABOOM / WONDERBOOM speakers",
    version="1.0.0",
    core=False,
)
class UEBoomParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        uuid_hit = any(
            _normalize_uuid(u) == _UE_SERVICE_UUID_NORM
            for u in (raw.service_uuids or [])
        )

        payload = raw.manufacturer_payload
        metadata: dict | None = None
        if (
            raw.company_id == LOGITECH_COMPANY_ID
            and payload is not None
            and len(payload) >= _PAYLOAD_LEN
        ):
            metadata = self._decode(payload)

        if metadata is None:
            if not uuid_hit:
                return None
            metadata = {"ad_format": "presence"}

        metadata["vendor"] = "Ultimate Ears (Logitech)"
        metadata["ue_service_uuid"] = uuid_hit
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        id_hash = hashlib.sha256(f"ueboom:{raw.mac_address}".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="ue_boom",
            beacon_type="ue_boom",
            device_class="audio",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def _decode(self, payload: bytes) -> dict | None:
        """Decode a 13-byte vendor payload, or None if it isn't UE-shaped."""
        pid = (payload[0] << 8) | payload[1]
        if pid == _WASP_PID:
            return self._decode_wasp(payload, pid)

        # Battery byte sanity gate: keeps non-speaker Logitech peripherals
        # (mice/keyboards using the same company ID) from being mis-decoded.
        battery = payload[0] & 0x7F
        if battery > 100:
            return None
        return self._decode_cpp(payload, battery)

    def _decode_wasp(self, payload: bytes, pid: int) -> dict:
        # Status byte at record offset 23 == payload[9].
        status = payload[9]
        return {
            "ad_format": "wasp",
            "pid": pid,
            "model": PRODUCT_IDS.get(pid, f"unknown_{pid:04x}"),
            "status_byte": status,
            "is_audio_source": bool(status & 0x80),
            "is_playing_audio": bool(status & 0x40),
            "is_playing_local_audio": bool(status & 0x20),
            # Bits 4 and 3 both map to isPlayingStreamingAudio in the app.
            "is_playing_streaming_audio": bool(status & 0x18),
            "is_powered": bool(status & 0x04),
            "group_id": status & 0x03,
        }

    def _decode_cpp(self, payload: bytes, battery: int) -> dict:
        status = payload[4]
        extra = payload[5]
        broadcast_status = (extra >> 5) & 0x07

        meta: dict = {
            "ad_format": "cpp_legacy",
            # Record offset 14: bit 7 = isPowered, bits [6:0] = battery %.
            "battery_percent": battery,
            "is_powered": bool(payload[0] & 0x80),
            "battery_flags": payload[1],
            "volume": payload[2],
            "events": payload[3],
            # Record offset 18 status byte.
            "status_byte": status,
            "bt_classic_connected": bool(status & 0x40),
            "internet_connected": bool(status & 0x20),
            "streaming_status": (status & 0x18) >> 3,
            "is_broadcasting": bool(status & 0x04),
            "is_button_pressed": bool(status & 0x01),
            # Record offset 19 extra-flags byte (XUP / PartyUp state).
            "extra_flags": extra,
            "broadcast_status": broadcast_status,
            "broadcast_status_name": BROADCAST_RECEIVER_STATUS.get(
                broadcast_status, f"unknown_{broadcast_status}"
            ),
            "connect_button": bool(extra & 0x10),
            "autoconnect": bool(extra & 0x08),
            "broadcast_known": bool(extra & 0x04),
            "audio_config": extra & 0x03,
            "name_revision": payload[12] & 0x0F,
        }

        # Record offsets 20-25: MAC of the PartyUp/XUP broadcast source.
        bmac = payload[6:12]
        if any(bmac) and bmac != b"\xff" * 6:
            meta["broadcast_mac"] = _mac(bmac)

        return meta

    def storage_schema(self):
        return None
