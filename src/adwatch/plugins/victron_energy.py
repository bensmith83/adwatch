"""Victron Energy "Instant Readout" plugin.

Layout verified against ``apk-ble-hunting`` report
``victronenergy-victronconnect_passive.md`` (disassembly of
``VeSmartDevice::parseAdvertisingData`` in ``libVictronConnect_*.so``,
cross-checked against the community ``victron-ble`` protocol notes).

Offsets are relative to :attr:`RawAdvertisement.manufacturer_payload` — the
bytes stored under the ``0x02E1`` manufacturer key, company ID already
stripped:

===========  ===  ============================================================
payload off  len  field
===========  ===  ============================================================
0            1    record type — always ``0x10`` for Instant Readout (gate)
1            1    readout flags: low nibble = record-format mode, bits 6/7 flags
2            2    ``model_id`` (u16 LE) — selects the per-model record class
4            1    ``readout_type`` — record sub-type (SolarCharger, BMV, …)
5            2    ``iv`` / nonce (u16 LE) — AES-CTR initial counter value
7            1    key-check byte — equals ``advertisement_key[0]`` in the clear
8..end       var  AES-128-CTR ciphertext (per-device 16-byte key required)
===========  ===  ============================================================

Everything from byte 8 on (voltage, current, SoC, power, temperature, alarms)
is encrypted with a per-device key that is never broadcast, so this parser
surfaces the clear-text header plus the ciphertext verbatim and does not
attempt decryption.  Victron units use a *static public* BLE address, so the
MAC is a sound identity anchor here.
"""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

VICTRON_COMPANY_ID = 0x02E1

# Gate byte at payload[0]: "Product Advertisement" / Instant Readout record.
INSTANT_READOUT_RECORD = 0x10

# payload[4] — record sub-type; names follow the app's own log strings and the
# community victron-ble AdvertisementRecordType enum.
RECORD_TYPES = {
    0x00: "Test Record",
    0x01: "Solar Charger",
    0x02: "Battery Monitor",     # BMV / SmartShunt
    0x03: "Inverter",
    0x04: "DC/DC Converter",
    0x05: "SmartLithium",
    0x06: "Inverter RS",
    0x07: "GX Device",
    0x08: "AC Charger",          # IP22 / IP43
    0x09: "Smart Battery Protect",
    0x0A: "Lynx Smart BMS",
    0x0B: "Multi RS",
    0x0C: "VE.Bus",
    0x0D: "DC Energy Meter",
    0x0F: "Orion XS",
}


@register_parser(
    name="victron_energy",
    company_id=VICTRON_COMPANY_ID,
    description="Victron Energy Instant Readout",
    version="1.1.0",
    core=False,
)
class VictronEnergyParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 4:
            return None
        if int.from_bytes(raw.manufacturer_data[:2], "little") != VICTRON_COMPANY_ID:
            return None

        payload = raw.manufacturer_payload
        # App gate: company == 0x02E1 && payload[0] == 0x10 && len(payload) >= 4.
        if not payload or len(payload) < 4:
            return None
        if payload[0] != INSTANT_READOUT_RECORD:
            return None

        flags = payload[1]
        model_id = struct.unpack_from("<H", payload, 2)[0]

        metadata: dict = {
            "model_id": model_id,
            "readout_flags": flags,
            "record_format_mode": flags & 0x0F,
            "flag_bit6": bool(flags & 0x40),
            "flag_bit7": bool(flags & 0x80),
        }

        if len(payload) >= 5:
            record_type = payload[4]
            metadata["record_type"] = record_type
            metadata["device_type"] = RECORD_TYPES.get(record_type, "Unknown")

        if len(payload) >= 7:
            iv = struct.unpack_from("<H", payload, 5)[0]
            metadata["data_counter"] = iv
            metadata["iv"] = iv

        if len(payload) >= 8:
            # Broadcast in the clear; equals advertisement_key[0]. A change here
            # means the owner rotated the key.
            metadata["key_check_byte"] = payload[7]

        ciphertext = payload[8:] if len(payload) > 8 else b""
        metadata["encrypted"] = bool(ciphertext)
        metadata["encrypted_len"] = len(ciphertext)
        if ciphertext:
            metadata["encrypted_payload_hex"] = ciphertext.hex()

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:{model_id}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="victron_energy",
            beacon_type="victron_energy",
            device_class="energy",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
