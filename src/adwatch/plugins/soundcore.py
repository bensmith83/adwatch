"""Anker / Oceanwing Soundcore audio plugin (best-effort).

Per apk-ble-hunting/reports/oceanwing-soundcore_passive.md:

  - The companion app is Flutter; BLE logic is in `libapp.so` Dart AOT
    snapshot, not statically recoverable.
  - Anticipated signals (from public Anker product knowledge):
      Anker company_id 0x07AB
      Name prefixes: "Soundcore ", "soundcore "

  Manufacturer-data byte layout TBD via Dart disassembly.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


ANKER_COMPANY_ID = 0x07AB

_NAME_RE = re.compile(r"^[Ss]oundcore ")


@register_parser(
    name="soundcore",
    company_id=ANKER_COMPANY_ID,
    local_name_pattern=r"^[Ss]oundcore ",
    description="Anker / Oceanwing Soundcore audio (best-effort)",
    version="1.0.0",
    core=False,
)
class SoundcoreParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        cid_hit = raw.company_id == ANKER_COMPANY_ID
        name_match = _NAME_RE.match(raw.local_name) if raw.local_name else None

        if not (cid_hit or name_match):
            return None

        metadata: dict = {"vendor": "Anker (Soundcore)"}

        payload = raw.manufacturer_payload
        if cid_hit and payload:
            metadata["mfr_payload_hex"] = payload.hex()
            metadata["mfr_payload_length"] = len(payload)
            # First byte often encodes a product/model code per Anker convention.
            if payload:
                metadata["product_code_byte"] = payload[0]

        if raw.local_name:
            metadata["device_name"] = raw.local_name
            if name_match:
                # Strip "Soundcore "/"soundcore " prefix for model hint.
                metadata["model_hint"] = raw.local_name[len("Soundcore "):]

        id_hash = hashlib.sha256(
            f"soundcore:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        raw_hex = raw.manufacturer_data.hex() if raw.manufacturer_data else ""

        return ParseResult(
            parser_name="soundcore",
            beacon_type="soundcore",
            device_class="audio",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )

    def storage_schema(self):
        return None
