"""Allegion Engage / Schlage Mobile Access commercial-lock plugin.

Per apk-ble-hunting/reports/schlage-mobileaccess_passive.md. Distinct
from `plugins/schlage.py` (which targets the Schlage residential line via
name regex). The Allegion commercial line (Encode Plus / NDE / ADE / LE /
Sense / Topaz / CO110 / Engage Plus / eSigno / XE360 / ZION / Interflex
— 35 variants) advertises a manufacturer-data record starting with the
sentinel ``[0x3B, 0x01]`` (interpreted as little-endian CID ``0x013B``).

Layout (post-CID):

  - [0]    adv_version (1 = legacy v1, 3+ = LTV-stream)
  - [1..2] device_type (big-endian) — 35-entry AlBLEDeviceType enum
  - **v1**:
      - [3] state (0x01 = factory_default, 0x02 = commissioned, 0x03 = unconnected)
      - [4] security_version
  - **v3+**:
      - [3] reserved
      - [4..] LTV stream of protocol blocks (ENGAGE / SENSE / SAPPHIRE /
        SIG_AUTH / IOT_NATIVE), each: ``length, type, value...`` until
        a length=0 terminator. Per-block bytes 0/1 carry state +
        security_version (high bit on ENGAGE = isDynamicMtuSupported).

Service-data carrying the lock serial number under AD types 0x10 / 0x16
is not parsed here (the registry doesn't surface non-UUID AD types in
``RawAdvertisement``); a downstream enrichment can add it once raw AD
records become available.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


ALLEGION_CID = 0x013B  # little-endian of [0x3B, 0x01] sentinel

_STATE_MAP = {
    0x01: "factory_default",
    0x02: "commissioned",
    0x03: "unconnected",
}

_PROTOCOL_BLOCK_TYPES = {
    1: "ENGAGE",
    2: "SENSE",
    3: "SAPPHIRE",
    4: "SIG_AUTH",
    5: "IOT_NATIVE",
}


@register_parser(
    name="allegion_engage",
    company_id=ALLEGION_CID,
    description="Allegion Engage / Schlage Mobile Access commercial locks",
    version="1.0.0",
    core=False,
)
class AllegionEngageParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if raw.company_id != ALLEGION_CID:
            return None

        payload = raw.manufacturer_payload or b""
        metadata: dict = {"vendor": "Allegion"}

        if len(payload) >= 1:
            adv_version = payload[0]
            metadata["adv_version"] = adv_version
        else:
            return self._build_result(raw, metadata)

        if len(payload) >= 3:
            metadata["device_type"] = (payload[1] << 8) | payload[2]

        if adv_version <= 2:
            # Legacy v1/v2 layout.
            if len(payload) >= 4:
                metadata["state"] = _STATE_MAP.get(payload[3], f"unknown_0x{payload[3]:02X}")
            if len(payload) >= 5:
                metadata["security_version"] = payload[4]
        else:
            # v3+: LTV stream starting at offset 4 (offset 3 is reserved).
            blocks = []
            i = 4
            while i < len(payload):
                length = payload[i]
                if length == 0:
                    break
                if i + 1 >= len(payload):
                    break
                btype = payload[i + 1]
                value_start = i + 2
                value_end = min(value_start + length, len(payload))
                value = payload[value_start:value_end]
                block: dict = {
                    "type": btype,
                    "type_name": _PROTOCOL_BLOCK_TYPES.get(btype, f"unknown_{btype}"),
                    "value_hex": value.hex(),
                }
                if len(value) >= 1:
                    block["state"] = _STATE_MAP.get(value[0], f"unknown_0x{value[0]:02X}")
                if len(value) >= 2:
                    sv = value[1]
                    block["security_version"] = sv & 0x7F
                    if btype == 1 and (sv & 0x80):
                        block["dynamic_mtu_supported"] = True
                blocks.append(block)
                # Stride: length-byte + type-byte + length value-bytes.
                i += length + 2
            metadata["protocol_blocks"] = blocks

        return self._build_result(raw, metadata)

    def _build_result(self, raw: RawAdvertisement, metadata: dict) -> ParseResult:
        id_basis = f"allegion_engage:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="allegion_engage",
            beacon_type="allegion_engage",
            device_class="lock",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
