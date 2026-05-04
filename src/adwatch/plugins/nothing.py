"""Nothing earbuds / CMF watch plugin.

Per apk-ble-hunting/reports/nothing-smartcenter_passive.md:

  - Google Fast Pair service-data on UUID 0xFE2C (canonical Fast Pair frame).
  - Manufacturer-data under one of three IDs:
      0x0CCB (3275, Nothing Technology Limited — SIG-assigned)
      0xCB0C (51980, byte-swapped variant seen in some firmware)
      0xFFFF (65535, reserved/sentinel)
  - Last 6 bytes of mfr-data = persistent device identifier (BD_ADDR-like).
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


NOTHING_COMPANY_ID = 0x0CCB
NOTHING_COMPANY_ID_BYTESWAPPED = 0xCB0C
NOTHING_COMPANY_ID_SENTINEL = 0xFFFF
FAST_PAIR_UUID = "fe2c"

ALL_NOTHING_CIDS = (
    NOTHING_COMPANY_ID,
    NOTHING_COMPANY_ID_BYTESWAPPED,
    NOTHING_COMPANY_ID_SENTINEL,
)


@register_parser(
    name="nothing",
    company_id=ALL_NOTHING_CIDS,
    service_uuid=FAST_PAIR_UUID,
    local_name_pattern=r"^(Nothing|CMF )",
    description="Nothing earbuds / CMF watch (Fast Pair + Nothing mfr-data)",
    version="1.0.0",
    core=False,
)
class NothingParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        cid = raw.company_id
        cid_hit = cid in ALL_NOTHING_CIDS
        fast_pair_data = (raw.service_data or {}).get(FAST_PAIR_UUID)
        name_hit = bool(raw.local_name and (
            raw.local_name.startswith("Nothing") or raw.local_name.startswith("CMF ")
        ))

        # Fast Pair alone is shared across many vendors; require a Nothing-specific
        # signal (CID or name) to claim attribution.
        if not (cid_hit or name_hit):
            return None

        metadata: dict = {"vendor": "Nothing"}
        if cid_hit:
            metadata["matched_company_id"] = cid

        payload = raw.manufacturer_payload
        persistent_id_hex = None
        if cid_hit and payload and len(payload) >= 6:
            # Last 6 bytes = persistent device ID (per parseNothingMac).
            persistent_id_hex = payload[-6:].hex()
            metadata["persistent_id_hex"] = persistent_id_hex

        if fast_pair_data:
            metadata["fast_pair_present"] = True
            metadata["fast_pair_data_hex"] = fast_pair_data.hex()
            if len(fast_pair_data) == 3:
                # Short form: 3-byte Fast Pair model ID (big-endian).
                metadata["fast_pair_model_id"] = (
                    (fast_pair_data[0] << 16)
                    | (fast_pair_data[1] << 8)
                    | fast_pair_data[2]
                )
                metadata["fast_pair_mode"] = "discoverable"
            elif len(fast_pair_data) >= 4:
                metadata["fast_pair_mode"] = "account_key_filter"

        # Both signals present = high-confidence Nothing
        if cid_hit and fast_pair_data:
            metadata["high_confidence"] = True

        if raw.local_name:
            metadata["device_name"] = raw.local_name

        if persistent_id_hex:
            id_basis = f"nothing:{persistent_id_hex}"
        else:
            id_basis = f"nothing:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        raw_hex = raw.manufacturer_data.hex() if raw.manufacturer_data else ""

        return ParseResult(
            parser_name="nothing",
            beacon_type="nothing",
            device_class="audio",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )

    def storage_schema(self):
        return None
