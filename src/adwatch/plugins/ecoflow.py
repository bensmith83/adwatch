"""EcoFlow portable power station plugin."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

ECOFLOW_COMPANY_ID = 0xB5B5

SERIAL_PREFIX_MAP = {
    "R331": "DELTA 2", "R335": "DELTA 2",
    "R351": "DELTA 2 Max", "R354": "DELTA 2 Max",
    "P231": "DELTA 3", "D3N1": "DELTA 3 Classic",
    "DCA": "DELTA Pro", "DCF": "DELTA Pro", "DCK": "DELTA Pro",
    "MR51": "DELTA Pro 3", "Y711": "DELTA Pro Ultra",
    "R601": "RIVER 2", "R603": "RIVER 2",
    "R611": "RIVER 2 Max", "R613": "RIVER 2 Max",
    "R631": "RIVER 3 Plus", "R634": "RIVER 3 Plus",
    "HW51": "PowerStream", "HD31": "Smart Home Panel 2",
    "DB": "DELTA mini",
}


@register_parser(
    name="ecoflow",
    company_id=ECOFLOW_COMPANY_ID,
    local_name_pattern=r"^EF-",
    description="EcoFlow power stations",
    version="1.0.0",
    core=False,
)
class EcoFlowParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 4:
            return None

        company_id = int.from_bytes(raw.manufacturer_data[:2], "little")
        if company_id != ECOFLOW_COMPANY_ID:
            return None

        payload = raw.manufacturer_data[2:]
        return self._parse_payload(raw, payload)

    def _parse_payload(self, raw, payload):
        protocol_version = payload[0]
        metadata = {"protocol_version": protocol_version}

        if len(payload) >= 17:
            serial_bytes = payload[1:17]
            try:
                serial = serial_bytes.decode("ascii").rstrip("\x00")
            except UnicodeDecodeError:
                serial = serial_bytes.hex()
            metadata["serial_number"] = serial
            metadata["device_model"] = self._model_from_serial(serial)

        if len(payload) >= 19:
            status = payload[17]
            metadata["active"] = bool(status & 0x80)
            metadata["product_type"] = payload[18]

        if len(payload) >= 23:
            caps = payload[22]
            metadata["encrypted"] = bool(caps & 0x01)
            metadata["supports_verification"] = bool(caps & 0x02)
            metadata["verified"] = bool(caps & 0x04)
            metadata["encryption_type"] = (caps & 0x38) >> 3
            metadata["supports_5ghz"] = bool(caps & 0x40)

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:ecoflow".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="ecoflow",
            beacon_type="ecoflow",
            device_class="power",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata=metadata,
        )

    def _model_from_serial(self, serial):
        for prefix, model in SERIAL_PREFIX_MAP.items():
            if serial.startswith(prefix):
                return model
        return "Unknown EcoFlow"
