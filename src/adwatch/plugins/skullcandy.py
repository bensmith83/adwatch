"""Skullcandy Skull-iQ earbud / headphone plugin.

Per apk-ble-hunting/reports/skullcandy-skulliq_passive.md. Skullcandy
products advertise a Bragi-SDK-format manufacturer-data block:

  - [0..1] Skullcandy SIG CID ``0x07C9`` (1993 — Skullcandy Inc.)
  - [2]    skip / padding byte (possible flag/version — not decoded)
  - [3]    model ID (Skullcandy.java: 9=Grind, 22=CHP200, 21=T80_PLUS,
            52=CHP300, 29=T99_PLUS, 45=T120, 8=Push Active, etc.)
  - [5..10] full 6-byte BD_ADDR of the device (used as identity-hash basis
            — survives BLE address randomization)

Plus name regex covering the model short-names (Grind / CHP200 / Method
360 ANC / Method 540 ANC / Skullcandy CRUSHER 1080 ANC / etc.).
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


SKULLCANDY_CID = 0x07C9  # 1993

MODEL_ID_TABLE = {
    8: "PUSH_ACTIVE",
    9: "GRIND",
    10: "GRIND_FUEL",
    21: "T80_PLUS",
    22: "CHP200",
    29: "T99_PLUS",
    45: "T120",
    52: "CHP300",
}

_NAME_RE = re.compile(
    r"^(Grind|Sesh Boost|Push Active|Oppactive|Opp active|"
    r"CHP\d{3}|S6CAW|T\d{2,3}\+?|S2IPW|S2RLW|railanc|rail|"
    r"Method 360 ANC|Method 540 ANC|"
    r"Skullcandy [A-Za-z]+|"
    r"S2)"
)


@register_parser(
    name="skullcandy",
    company_id=SKULLCANDY_CID,
    local_name_pattern=r"^(Grind|Sesh Boost|Push Active|CHP\d{3}|T\d{2,3}|Method|Skullcandy)",
    description="Skullcandy Skull-iQ earbuds / headphones (Bragi SDK)",
    version="1.0.0",
    core=False,
)
class SkullcandyParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        cid_hit = raw.company_id == SKULLCANDY_CID
        local_name = raw.local_name or ""
        name_hit = bool(_NAME_RE.match(local_name))

        if not (cid_hit or name_hit):
            return None

        metadata: dict = {"vendor": "Skullcandy"}
        if local_name:
            metadata["device_name"] = local_name

        embedded_mac: str | None = None
        if cid_hit:
            payload = raw.manufacturer_payload or b""
            if len(payload) >= 2:
                model_id = payload[1]
                metadata["model_id"] = model_id
                metadata["model"] = MODEL_ID_TABLE.get(model_id, f"unknown_0x{model_id:02X}")
            if len(payload) >= 8:
                # payload (post-CID) layout:
                #   [0]    skip / padding byte
                #   [1]    model ID
                #   [2..7] full 6-byte BD_ADDR
                mac_bytes = payload[2:8]
                embedded_mac = ":".join(f"{b:02X}" for b in mac_bytes)
                metadata["embedded_mac"] = embedded_mac

        if embedded_mac:
            id_basis = f"skullcandy:{embedded_mac}"
        else:
            id_basis = f"skullcandy:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="skullcandy",
            beacon_type="skullcandy",
            device_class="audio",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
