"""Pokemon GO Plus + BLE advertisement parser.

The Pokemon GO Plus + (PGP+) is a Nintendo gaming accessory that advertises
with company ID 0x0553 (Nintendo) and local name "Pokemon GO Plus +".
"""

import hashlib
import re

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import register_parser

NINTENDO_COMPANY_ID = 0x0553
NAME_RE = re.compile(r"^Pokemon GO Plus")


@register_parser(
    name="pokemon_go_plus",
    company_id=NINTENDO_COMPANY_ID,
    local_name_pattern=r"^Pokemon GO Plus",
    description="Pokemon GO Plus + gaming accessory advertisements",
    version="1.0.0",
    core=False,
)
class PokemonGoPlusParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        name_match = raw.local_name is not None and NAME_RE.match(raw.local_name)
        company_match = raw.company_id == NINTENDO_COMPANY_ID

        if not name_match and not company_match:
            return None

        id_hash = hashlib.sha256(f"pokemon_go_plus:{raw.mac_address}".encode()).hexdigest()[:16]

        metadata: dict = {}
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        if raw.manufacturer_payload:
            metadata["payload_hex"] = raw.manufacturer_payload.hex()

        raw_hex = raw.manufacturer_data.hex() if raw.manufacturer_data else ""

        return ParseResult(
            parser_name="pokemon_go_plus",
            beacon_type="pokemon_go_plus",
            device_class="gaming_accessory",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )
