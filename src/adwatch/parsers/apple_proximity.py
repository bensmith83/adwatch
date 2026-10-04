"""Apple Proximity Pairing parser (AirPods/Beats).

Beats enrichment (apk-ble-hunting apple-bnd report, Beats app p1/e.java +
p1/f.java). Offsets use ``msd`` = manufacturer payload after the 2-byte CID:

- compact layout (msd[2] != 0, AirPods-style): existing nibble decode.
- extended layout (msd[0]==0x07, msd[2]==0x00, len(msd)>=17; Beats B2P/BCD):
  product_id u16 LE @3-4, B2P persistent 6-byte address @5-10, battery
  0-100 + charging bit7 @12 (R) / 13 (L) / 14 (case), color msd[15] & 7.
  BCD is the ``07 0F 00`` prefix.
- BTP family (msd[1]==0x90, msd[0] masked): product_id u16 LE @2-3, battery
  nibbles x10 at msd[6] (R low / L high) and msd[7] low (case).
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

PROXIMITY_TYPE = 0x07
BTP_MARKER = 0x90

# Apple TLV types owned by other core Apple parsers (continuity, airdrop,
# airplay, nearby_action, findmy, ibeacon). A BTP ad's first byte is masked
# by the Beats app, so only claim BTP when it can't collide with them.
OTHER_APPLE_TLV_TYPES = frozenset({
    0x01, 0x02, 0x05, 0x06, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F,
    0x10, 0x12, 0x16,
})

MODEL_NAMES = {
    0x0220: "AirPods 1st Gen",
    0x0F20: "AirPods 2nd Gen",
    0x1320: "AirPods 3rd Gen",
    0x0A20: "AirPods Pro",
    0x1420: "AirPods Pro 2",
    0x0B20: "AirPods Max",
    0x0520: "Beats Solo Pro",
    0x0620: "Beats Studio Buds",
    0x0320: "Powerbeats Pro",
    0x1020: "Beats Fit Pro",
    0x1220: "Beats Studio Buds+",
}


@register_parser(
    name="apple_proximity",
    company_id=0x004C,
    description="Apple Proximity Pairing (AirPods/Beats)",
    version="1.0",
    core=True,
)
class AppleProximityParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        data = raw.manufacturer_data
        if not data or len(data) < 4:
            return None

        company_id = int.from_bytes(data[:2], "little")
        if company_id != 0x004C:
            return None

        tlv_type = data[2]
        msd = data[2:]

        if len(msd) >= 2 and msd[1] == BTP_MARKER:
            if tlv_type != PROXIMITY_TYPE and tlv_type in OTHER_APPLE_TLV_TYPES:
                return None
            return self._parse_btp(raw, msd)

        if tlv_type != PROXIMITY_TYPE:
            return None

        if len(msd) >= 17 and msd[2] == 0x00:
            return self._parse_extended(raw, msd)

        tlv_len = data[3]
        tlv_value = data[4:]
        if len(tlv_value) < 7:
            return None

        device_model = (tlv_value[1] << 8) | tlv_value[2]
        utp = tlv_value[3]

        battery_byte1 = tlv_value[4]
        battery_left_raw = (battery_byte1 >> 4) & 0x0F
        battery_right_raw = battery_byte1 & 0x0F

        battery_byte2 = tlv_value[5]
        battery_case_raw = (battery_byte2 >> 4) & 0x0F
        lid_nibble = battery_byte2 & 0x0F

        battery_left = min(battery_left_raw * 10, 100)
        battery_right = min(battery_right_raw * 10, 100)
        battery_case = min(battery_case_raw * 10, 100)

        model_hex = f"{device_model:04x}"
        first_7 = tlv_value[:7]
        identifier_hash = hashlib.sha256(
            f"{raw.mac_address}:{model_hex}:{first_7.hex()}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="apple_proximity",
            beacon_type="apple_proximity",
            device_class="accessory",
            identifier_hash=identifier_hash,
            raw_payload_hex=data[2:].hex(),
            metadata={
                "device_model": device_model,
                "product_id": tlv_value[1] | (tlv_value[2] << 8),
                "layout": "compact",
                "model_name": MODEL_NAMES.get(device_model, "Unknown"),
                "battery_left": battery_left,
                "battery_right": battery_right,
                "battery_case": battery_case,
                "utp": utp,
                "lid_open": lid_nibble != 0,
                "charging_left": bool(utp & 0x01),
                "charging_right": bool(utp & 0x02),
                "charging_case": bool(utp & 0x04),
                "in_ear_left": bool(utp & 0x08),
                "in_ear_right": bool(utp & 0x10),
            },
        )

    def _parse_extended(self, raw: RawAdvertisement, msd: bytes) -> ParseResult:
        family = "BCD" if msd[1] == 0x0F else "B2P"
        product_id = msd[3] | (msd[4] << 8)
        device_model = (msd[3] << 8) | msd[4]
        metadata = {
            "device_model": device_model,
            "product_id": product_id,
            "model_name": MODEL_NAMES.get(device_model, "Unknown"),
            "layout": "extended",
            "beats_family": family,
            "battery_right": msd[12] & 0x7F,
            "battery_left": msd[13] & 0x7F,
            "battery_case": msd[14] & 0x7F,
            "charging_right": bool(msd[12] & 0x80),
            "charging_left": bool(msd[13] & 0x80),
            "charging_case": bool(msd[14] & 0x80),
            "bud_flags": msd[11],
            "lid_byte": msd[16],
        }
        if family == "B2P":
            address = ":".join(f"{b:02X}" for b in msd[5:11])
            metadata["device_address"] = address
            metadata["color_id"] = msd[15] & 0x07
            id_basis = f"beats:{address}"
        else:
            id_basis = f"{raw.mac_address}:{product_id:04x}:beats_bcd"
        return ParseResult(
            parser_name="apple_proximity",
            beacon_type="apple_proximity",
            device_class="accessory",
            identifier_hash=hashlib.sha256(id_basis.encode()).hexdigest()[:16],
            raw_payload_hex=msd.hex(),
            metadata=metadata,
        )

    def _parse_btp(self, raw: RawAdvertisement, msd: bytes) -> ParseResult | None:
        if len(msd) < 4:
            return None
        product_id = msd[2] | (msd[3] << 8)
        metadata = {
            "product_id": product_id,
            "layout": "compact",
            "beats_family": "BTP",
        }
        if len(msd) >= 8:
            nibbles = {
                "battery_right": msd[6] & 0x0F,
                "battery_left": msd[6] >> 4,
                "battery_case": msd[7] & 0x0F,
            }
            for key, val in nibbles.items():
                if val <= 10:
                    metadata[key] = val * 10
        id_basis = f"{raw.mac_address}:{product_id:04x}:beats_btp"
        return ParseResult(
            parser_name="apple_proximity",
            beacon_type="apple_proximity",
            device_class="accessory",
            identifier_hash=hashlib.sha256(id_basis.encode()).hexdigest()[:16],
            raw_payload_hex=msd.hex(),
            metadata=metadata,
        )
