"""BM2 car battery monitor plugin — 12V battery voltage via AES-encrypted BLE ads."""

import hashlib

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

BM2_KEY = b'leagend\xff\xfe188246\x00'  # 16 bytes, null-padded
BM2_IV = b'\x00' * 16


@register_parser(
    name="bm2_battery",
    local_name_pattern=r"^(Battery Monitor|ZX-1689)$",
    service_uuid="fff0",
    description="BM2 car battery monitor (12V voltage)",
    version="1.0.0",
    core=False,
)
class BM2BatteryParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 16:
            return None

        encrypted = raw.manufacturer_data
        cipher = Cipher(algorithms.AES(BM2_KEY), modes.CBC(BM2_IV))
        decryptor = cipher.decryptor()
        plaintext = decryptor.update(encrypted) + decryptor.finalize()

        raw_voltage = (plaintext[1] << 8) | plaintext[2]
        voltage = (raw_voltage >> 4) / 100.0

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:bm2_battery".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="bm2_battery",
            beacon_type="bm2_battery",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=encrypted.hex(),
            metadata={
                "voltage": voltage,
                "encrypted": True,
                "device_name": raw.local_name,
            },
        )

    def storage_schema(self):
        return None
