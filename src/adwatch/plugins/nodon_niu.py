"""NodOn NIU smart button plugin."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

BUTTON_EVENTS = {
    0x01: "single",
    0x02: "double",
    0x03: "triple",
    0x04: "quad",
    0x05: "quintuple",
    0x09: "long_press",
    0x0A: "release",
}

COLORS = {
    0x01: "white",
    0x02: "blue",
    0x03: "green",
    0x04: "red",
    0x05: "black",
}


@register_parser(
    name="nodon_niu",
    local_name_pattern=r"NIU",
    description="NodOn NIU smart button",
    version="1.0.0",
    core=False,
)
class NodOnNiuParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        payload = raw.manufacturer_payload
        if not payload or len(payload) < 3:
            return None

        event_code = payload[0]
        color_code = payload[1]
        battery = payload[2]

        event = BUTTON_EVENTS.get(event_code)
        if event is None:
            return None

        color = COLORS.get(color_code)
        if color is None:
            return None

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:nodon_niu".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="nodon_niu",
            beacon_type="nodon_niu",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=payload[:3].hex(),
            metadata={
                "button_event": event,
                "button_color": color,
                "battery": battery,
            },
        )

    def storage_schema(self):
        return None
