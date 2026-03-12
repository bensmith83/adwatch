"""Google Find My Device Network BLE parser plugin."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

FMDN_UUID = "0000fe2c-0000-1000-8000-00805f9b34fb"
GOOGLE_COMPANY_ID = 0x00E0
MIN_SERVICE_DATA_LEN = 21  # 1 (frame type) + 20 (EID)
MIN_MFR_PAYLOAD_LEN = 2   # device_type + tx_power

DEVICE_TYPE_MAP = {
    0x01: "phone",
    0x02: "tracker",
    0x03: "headphones",
    0x04: "accessory",
}


@register_parser(
    name="google_fmd",
    service_uuid=FMDN_UUID,
    company_id=GOOGLE_COMPANY_ID,
    description="Google Find My Device Network",
    version="1.0.0",
    core=False,
)
class GoogleFMDParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        id_hash = hashlib.sha256(raw.mac_address.encode()).hexdigest()[:16]

        # Service data takes priority
        if raw.service_data and FMDN_UUID in raw.service_data:
            data = raw.service_data[FMDN_UUID]
            if len(data) < MIN_SERVICE_DATA_LEN:
                return None
            return self._parse_service_data(data, id_hash)

        # Fall back to manufacturer data
        if raw.manufacturer_data and len(raw.manufacturer_data) >= 2:
            company_id = int.from_bytes(raw.manufacturer_data[:2], "little")
            if company_id != GOOGLE_COMPANY_ID:
                return None
            payload = raw.manufacturer_data[2:]
            if len(payload) < MIN_MFR_PAYLOAD_LEN:
                return None
            return self._parse_manufacturer_data(payload, id_hash)

        return None

    def _parse_service_data(self, data: bytes, id_hash: str) -> ParseResult:
        frame_type = data[0]
        eid = data[1:21]
        metadata = {
            "frame_type": frame_type,
            "protocol_version": frame_type,
            "eid": eid.hex(),
        }
        if len(data) > MIN_SERVICE_DATA_LEN:
            metadata["hashed_flags"] = data[21]

        return ParseResult(
            parser_name="google_fmd",
            beacon_type="google_fmd",
            device_class="tracker",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata=metadata,
        )

    def _parse_manufacturer_data(self, payload: bytes, id_hash: str) -> ParseResult:
        device_type_byte = payload[0]
        tx_power = int.from_bytes(payload[1:2], "big", signed=True)
        device_type = DEVICE_TYPE_MAP.get(device_type_byte, "unknown")

        return ParseResult(
            parser_name="google_fmd",
            beacon_type="google_fmd",
            device_class=device_type,
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata={
                "device_type": device_type,
                "tx_power": tx_power,
            },
        )
