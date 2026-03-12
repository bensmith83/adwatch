"""Apple Find My parser."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

FINDMY_TYPE = 0x12

_BATTERY_STATUS = {0x1: "full", 0x5: "medium", 0x9: "low", 0xD: "critical"}

_DEVICE_TYPES = {0: "airtag", 1: "apple_device", 2: "airpods", 3: "third_party"}

_DEVICE_CLASS = {
    "airtag": "tracker",
    "apple_device": "phone",
    "airpods": "accessory",
    "third_party": "tracker",
}


@register_parser(
    name="apple_findmy",
    company_id=0x004C,
    description="Apple Find My network tracker",
    version="1.0",
    core=True,
)
class AppleFindMyParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        data = raw.manufacturer_data
        if not data or len(data) < 6:
            return None

        company_id = int.from_bytes(data[:2], "little")
        if company_id != 0x004C:
            return None

        tlv_type = data[2]
        if tlv_type != FINDMY_TYPE:
            return None

        tlv_len = data[3]
        tlv_value = data[4:]
        if len(tlv_value) < tlv_len or tlv_len < 2:
            return None

        status_byte = tlv_value[0]
        ec_key_fragment = tlv_value[1:tlv_len]
        payload_hex = ec_key_fragment.hex()

        battery_status = _BATTERY_STATUS.get(status_byte >> 4, "unknown")
        device_type_bits = (status_byte >> 2) & 0x03
        findmy_device_type = _DEVICE_TYPES[device_type_bits]
        separated = bool(status_byte & 0x02)
        device_class = _DEVICE_CLASS[findmy_device_type]

        identifier_hash = hashlib.sha256(
            f"{raw.mac_address}:{payload_hex}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="apple_findmy",
            beacon_type="apple_findmy",
            device_class=device_class,
            identifier_hash=identifier_hash,
            raw_payload_hex=data[2:].hex(),
            metadata={
                "ec_key_fragment": payload_hex,
                "battery_status": battery_status,
                "findmy_device_type": findmy_device_type,
                "separated": separated,
            },
        )
