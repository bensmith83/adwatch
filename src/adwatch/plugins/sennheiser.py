"""Sennheiser / Sonova consumer-audio plugin.

Per apk-ble-hunting/reports/sennheiser-control_passive.md:

  - Sennheiser SIG service UUID 0xFDCE.
  - Sonova SIG service UUID 0xFCFE (post-2021 acquisition).
  - AMBEO Soundbar WiFi-pairing UUID CEE499E3-43A8-51D2-E7F4-1626AD235C0F.
  - Sennheiser company_id 0x0494 (1172).
  - Sonova company_id 0x0BA3 (2979).

Mfr-data is a TLV map (parsed in Hermes JS, not statically decodable):
  key 0  = RANDOMIZED_MAC_ADDRESS
  key 1  = PUBLIC_MAC_ADDRESS (encrypted)
  key -1 = SOUNDBAR_NETWORK_STATE
  key -2 = DEVICE_TYPE_AND_COLOR
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


SENNHEISER_COMPANY_ID = 0x0494
SONOVA_COMPANY_ID = 0x0BA3

SENNHEISER_SERVICE_UUID = "fdce"
SONOVA_SERVICE_UUID = "fcfe"
AMBEO_POPCORN_UUID = "cee499e3-43a8-51d2-e7f4-1626ad235c0f"


@register_parser(
    name="sennheiser",
    company_id=(SENNHEISER_COMPANY_ID, SONOVA_COMPANY_ID),
    service_uuid=(SENNHEISER_SERVICE_UUID, SONOVA_SERVICE_UUID, AMBEO_POPCORN_UUID),
    local_name_pattern=r"^(Momentum|CX|HD |IE |AMBEO|Sennheiser)",
    description="Sennheiser / Sonova consumer audio (incl. AMBEO Soundbar)",
    version="1.0.0",
    core=False,
)
class SennheiserParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        cid = raw.company_id
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        sen_uuid_hit = SENNHEISER_SERVICE_UUID in normalized
        sonova_uuid_hit = SONOVA_SERVICE_UUID in normalized
        ambeo_hit = AMBEO_POPCORN_UUID in normalized
        cid_sen_hit = cid == SENNHEISER_COMPANY_ID
        cid_sonova_hit = cid == SONOVA_COMPANY_ID
        # Strip optional `LE-` / `LE ` prefix per the bundle's regex, then
        # check against the brand prefix list.
        stripped_name = raw.local_name
        if stripped_name and (stripped_name.startswith("LE-") or stripped_name.startswith("LE ")):
            stripped_name = stripped_name[3:]
        import re as _re
        _name_re = _re.compile(r"^(Momentum|CX|HD |IE |AMBEO|Sennheiser)")
        name_match = bool(stripped_name and _name_re.match(stripped_name))

        if not (sen_uuid_hit or sonova_uuid_hit or ambeo_hit or cid_sen_hit
                or cid_sonova_hit or name_match):
            return None

        metadata: dict = {}

        if sen_uuid_hit or cid_sen_hit:
            metadata["brand"] = "Sennheiser"
        elif sonova_uuid_hit or cid_sonova_hit:
            metadata["brand"] = "Sonova"

        if ambeo_hit:
            metadata["product_line"] = "AMBEO_Soundbar"
            metadata["wifi_setup_mode"] = True

        if stripped_name:
            metadata["device_name"] = stripped_name
            metadata["model_hint"] = stripped_name

        # Preserve mfr-data payload as opaque hex — TLV decoded in Hermes JS.
        if raw.manufacturer_payload and (cid_sen_hit or cid_sonova_hit):
            metadata["mfr_payload_hex"] = raw.manufacturer_payload.hex()

        id_hash = hashlib.sha256(
            f"sennheiser:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        raw_hex = raw.manufacturer_data.hex() if raw.manufacturer_data else ""

        return ParseResult(
            parser_name="sennheiser",
            beacon_type="sennheiser",
            device_class="audio",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )

    def storage_schema(self):
        return None
