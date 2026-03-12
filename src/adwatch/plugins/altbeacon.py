"""AltBeacon BLE advertisement parser plugin."""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult


BEACON_CODE = b"\xBE\xAC"
MIN_DATA_LEN = 26


class AltBeaconParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        data = raw.manufacturer_data
        if not data or len(data) < MIN_DATA_LEN:
            return None

        if data[2:4] != BEACON_CODE:
            return None

        uuid_bytes = data[4:20]
        uuid = (
            f"{uuid_bytes[0:4].hex()}-{uuid_bytes[4:6].hex()}-"
            f"{uuid_bytes[6:8].hex()}-{uuid_bytes[8:10].hex()}-"
            f"{uuid_bytes[10:16].hex()}"
        )
        major = struct.unpack(">H", data[20:22])[0]
        minor = struct.unpack(">H", data[22:24])[0]
        ref_rssi = struct.unpack("b", data[24:25])[0]
        mfg_reserved = data[25]

        identifier_hash = hashlib.sha256(
            f"{uuid}:{major}:{minor}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="altbeacon",
            beacon_type="altbeacon",
            device_class="beacon",
            identifier_hash=identifier_hash,
            raw_payload_hex=data[2:].hex(),
            metadata={
                "uuid": uuid,
                "major": major,
                "minor": minor,
                "reference_rssi": ref_rssi,
                "mfg_reserved": mfg_reserved,
            },
        )
