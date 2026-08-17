"""Blue Spark Technologies TempTraq continuous-temperature patch plugin.

Byte layout per apk-ble-hunting/reports/bluesparktechnologies-temptraq_passive.md.

TempTraq is a pure passive broadcaster — the app never opens a GATT connection,
so the full clinical telemetry (patch serial, 18-bit sample index, status flags,
one live temperature plus 14 back-fill samples) rides unencrypted in the
manufacturer-data element of every advertisement.

The report indexes the whole AD (`bArr`): the mfr element header is at
bArr[4..5], the company ID at bArr[6..7], so `manufacturer_payload[i]` is
`bArr[i + 8]`:

    payload[0]      packet type / model marker (cadence: 24h/48h/72h patch)
    payload[1..3]   24-bit patch serial      (frame format 2)
    payload[0..3]   32-bit patch serial      (frame format 3; 24-bit if [0]==1)
    payload[4]      frame format, low nibble
    payload[5]      bit7 battery/alarm, bit6 R0, bits2-5 frame-type gate,
                    bits0-1 sample-index bits 16-17
    payload[6..7]   sample-index mid/low
    payload[8]      current temperature sample
    payload[9..22]  14 back-fill temperature samples

Company IDs: the app reads them big-endian (`0x005A` / `0x7704`), so on air the
bytes are `00 5A` and `77 04` — little-endian values 0x5A00 and 0x0477
("Blue Spark Technologies" in the SIG registry).
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


TEMPTRAQ_SERVICE_UUID = "c2fe"
# Little-endian on-air values of the app's big-endian constants 0x005A/0x7704.
TEMPTRAQ_COMPANY_IDS = (0x0477, 0x5A00)

MIN_PAYLOAD_LEN = 23  # 25-byte mfr element minus the 2-byte company ID

# Packet type -> (sample count, span in seconds) — frames/a.java:67-96.
PACKET_TYPE_CADENCE = {
    0x01: (720, 86400),      # 24 h patch
    0x02: (1440, 172800),    # 48 h patch
    0x03: (2160, 259200),    # 72 h patch
    0x04: (2160, 259200),
    0x05: (2160, 259200),
    0xF0: (2160, 259200),
}
VALID_PACKET_TYPES = frozenset(PACKET_TYPE_CADENCE)

# Status codes rather than readings (frames/c/b.java:37-63).
TEMPERATURE_SENTINELS = {0xFA, 0xFB, 0xFC, 0xFD, 0xFE, 0xFF}
FORMAT3_ONLY_SENTINEL = 0xF9

# frames/a.java:112-114 — packet type 0xF0 carries a -0.28 deg C calibration.
F0_TEMPERATURE_OFFSET = -0.28

CURRENT_SAMPLE_OFFSET = 8
HISTORY_SAMPLE_COUNT = 14


def decode_temperature(raw: int, packet_type: int = 0x02,
                       frame_format: int = 2) -> float | None:
    """Decode one temperature byte to degrees C, or None for a status sentinel."""
    if raw in TEMPERATURE_SENTINELS:
        return None
    if frame_format == 3 and raw == FORMAT3_ONLY_SENTINEL:
        return None
    temp = round((raw + 2200) / 20.0 - 80.0, 2)
    if temp > 4.0 and packet_type == 0xF0:
        temp = round(temp + F0_TEMPERATURE_OFFSET, 2)
    if temp < 4.0:
        return None
    return temp


def decode_sample_index(payload: bytes) -> int:
    """18-bit rolling sample index: [7] | ([6] << 8) | (([5] & 3) << 16)."""
    return payload[7] | (payload[6] << 8) | ((payload[5] & 0x03) << 16)


def decode_serial(payload: bytes) -> int:
    """Patch serial — 24-bit for frame format 2, 32-bit for frame format 3."""
    frame_format = payload[4] & 0x0F
    serial_24 = (payload[1] << 16) | (payload[2] << 8) | payload[3]
    if frame_format == 3 and payload[0] != 0x01:
        return (payload[0] << 24) | serial_24
    return serial_24


@register_parser(
    name="temptraq",
    company_id=list(TEMPTRAQ_COMPANY_IDS),
    service_uuid=TEMPTRAQ_SERVICE_UUID,
    description="Blue Spark TempTraq continuous temperature patch",
    version="1.0.0",
    core=False,
)
class TempTraqParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        advertised = {u.lower() for u in (raw.service_uuids or [])}
        advertised |= {k.lower() for k in (raw.service_data or {})}
        uuid_hit = TEMPTRAQ_SERVICE_UUID in advertised or any(
            u.startswith("0000c2fe-") for u in advertised
        )
        cid_hit = raw.company_id in TEMPTRAQ_COMPANY_IDS

        if not (uuid_hit or cid_hit):
            return None

        payload = raw.manufacturer_payload
        if not payload or len(payload) < MIN_PAYLOAD_LEN:
            return None

        packet_type = payload[0]
        if packet_type not in VALID_PACKET_TYPES:
            return None

        frame_format = payload[4] & 0x0F
        serial = decode_serial(payload)
        serial_hex = f"{serial:06x}" if serial <= 0xFFFFFF else f"{serial:08x}"
        sample_index = decode_sample_index(payload)
        status = payload[5]
        samples, span_s = PACKET_TYPE_CADENCE[packet_type]

        metadata: dict = {
            "vendor": "Blue Spark Technologies",
            "packet_type": packet_type,
            "packet_type_hex": f"{packet_type:02x}",
            "patch_serial": serial,
            "patch_serial_hex": serial_hex,
            "frame_format": frame_format,
            "sample_index": sample_index,
            "sample_count": samples,
            "sample_period_s": round(span_s / samples, 2),
            "patch_duration_hours": span_s // 3600,
            "battery_alarm_flag": bool(status & 0x80),
            "r0_flag": bool(status & 0x40),
            "frame_type_bits": (status >> 2) & 0x0F,
            # frames/b.java:60-83 — SC0/SC1 special-command frames otherwise.
            "is_data_frame": (status & 0x3C) == 0 and (sample_index & 0x03) != 3,
        }
        if uuid_hit:
            metadata["service_uuid_match"] = True

        current = decode_temperature(payload[CURRENT_SAMPLE_OFFSET],
                                     packet_type, frame_format)
        if current is not None:
            metadata["temperature_c"] = current
            metadata["temperature_f"] = round(current * 9 / 5 + 32, 2)

        history: list[float] = []
        for i in range(HISTORY_SAMPLE_COUNT):
            value = decode_temperature(
                payload[CURRENT_SAMPLE_OFFSET + 1 + i], packet_type, frame_format
            )
            if value is not None:
                history.append(value)
        metadata["history_count"] = len(history)
        if history:
            metadata["history_temps_c"] = ",".join(str(v) for v in history)
            metadata["temp_min_c"] = min(history)
            metadata["temp_max_c"] = max(history)

        # The patch serial is broadcast in every packet and outlives MAC
        # rotation, so it is both the identity basis and the dedup key (the
        # payload itself changes every advertisement).
        stable_key = f"temptraq:{serial_hex}"
        id_hash = hashlib.sha256(stable_key.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="temptraq",
            beacon_type="temptraq",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata=metadata,
            stable_key=stable_key,
        )
