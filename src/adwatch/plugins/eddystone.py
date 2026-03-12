"""Eddystone BLE beacon parser plugin."""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

EDDYSTONE_UUID = "feaa"

URL_SCHEMES = {
    0x00: "http://www.",
    0x01: "https://www.",
    0x02: "http://",
    0x03: "https://",
}


@register_parser(
    name="eddystone",
    service_uuid=EDDYSTONE_UUID,
    description="Eddystone BLE beacon advertisements",
    version="1.0.0",
    core=False,
)
class EddystoneParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.service_data or EDDYSTONE_UUID not in raw.service_data:
            return None

        data = raw.service_data[EDDYSTONE_UUID]
        if not data:
            return None

        frame_type = data[0]

        if frame_type == 0x00:
            return self._parse_uid(data, raw)
        elif frame_type == 0x10:
            return self._parse_url(data, raw)
        elif frame_type == 0x20:
            return self._parse_tlm(data, raw)
        elif frame_type == 0x30:
            return self._parse_eid(data, raw)
        return None

    def _parse_uid(self, data: bytes, raw: RawAdvertisement) -> ParseResult | None:
        if len(data) < 18:
            return None
        tx_power = struct.unpack_from("b", data, 1)[0]
        namespace = data[2:12]
        instance = data[12:18]
        id_hash = hashlib.sha256(
            f"{namespace.hex()}:{instance.hex()}".encode()
        ).hexdigest()[:16]
        return ParseResult(
            parser_name="eddystone",
            beacon_type="eddystone_uid",
            device_class="beacon",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata={
                "frame_type": "uid",
                "tx_power": tx_power,
                "namespace": namespace.hex(),
                "instance": instance.hex(),
            },
        )

    def _parse_url(self, data: bytes, raw: RawAdvertisement) -> ParseResult | None:
        if len(data) < 3:
            return None
        tx_power = struct.unpack_from("b", data, 1)[0]
        scheme_byte = data[2]
        scheme = URL_SCHEMES.get(scheme_byte, "")
        url = scheme + data[3:].decode("ascii", errors="replace")
        id_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
        return ParseResult(
            parser_name="eddystone",
            beacon_type="eddystone_url",
            device_class="beacon",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata={
                "frame_type": "url",
                "tx_power": tx_power,
                "url": url,
            },
        )

    def _parse_tlm(self, data: bytes, raw: RawAdvertisement) -> ParseResult | None:
        if len(data) < 14:
            return None
        version = data[1]
        battery_mv, temp_int, temp_frac, adv_count, uptime_units = struct.unpack_from(
            ">HbbII", data, 2
        )
        temperature = temp_int + (temp_frac & 0xFF) / 256.0
        id_hash = hashlib.sha256(
            f"{raw.mac_address}:{data.hex()}".encode()
        ).hexdigest()[:16]
        return ParseResult(
            parser_name="eddystone",
            beacon_type="eddystone_tlm",
            device_class="beacon",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata={
                "frame_type": "tlm",
                "battery_mv": battery_mv,
                "temperature": temperature,
                "adv_count": adv_count,
                "uptime_seconds": uptime_units * 0.1,
            },
        )

    def _parse_eid(self, data: bytes, raw: RawAdvertisement) -> ParseResult | None:
        if len(data) < 10:
            return None
        tx_power = struct.unpack_from("b", data, 1)[0]
        ephemeral = data[2:10]
        id_hash = hashlib.sha256(
            f"{raw.mac_address}:{ephemeral.hex()}".encode()
        ).hexdigest()[:16]
        return ParseResult(
            parser_name="eddystone",
            beacon_type="eddystone_eid",
            device_class="beacon",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata={
                "frame_type": "eid",
                "tx_power": tx_power,
                "ephemeral_id": ephemeral.hex(),
            },
        )
