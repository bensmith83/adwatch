"""Kwikset / Spectrum Brands smart lock BLE advertisement parser.

Per apk-ble-hunting/reports/kwikset-blewifi_passive.md. Four mfr-data variants
(consumer/auraReach/halo3/multifamily) identified by offsets and length; all
use Spectrum Brands SIG company ID 0x0356.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


SPECTRUM_COMPANY_ID = 0x0356

# Advertised service UUIDs for scan-filter matching.
LOCK_SYSTEM_UUID   = "4d050010-766c-42c4-8944-42bc98fc2d09"
ACTIVATION_UUID    = "4d050080-766c-42c4-8944-42bc98fc2d09"
SYSTEM_UUID        = "4d050090-766c-42c4-8944-42bc98fc2d09"
OTA_UUID           = "4d0500a0-766c-42c4-8944-42bc98fc2d09"

# Variant schemas — (label, total_len_mfr, company_offset, uniqueId_start, uniqueId_end, product_offset, ble_status_offset, operating_mode_offset, protocol_offset, pairing_flag_offset, gen_notif_offset, ac_notif_offset, pan_offset, lock_status_offset)
# Offsets are on the raw mfr data bytes *including* any inline company ID.
# -1 means the field is absent from this variant.
_VARIANTS = [
    # name           total  cid   uid_s uid_e prod blst op   prot pair gen  ac   pan  lock
    ("halo3",        19,    9,    0,    8,    11,  12,  -1,  13,  14,  15,  16,  17,  20),
    ("consumer",     15,    9,    0,    8,    11,  12,  -1,  13,  14,  15,  16,  -1,  -1),
    ("auraReach",    15,    0,    2,    10,   11,  12,  -1,  13,  14,  15,  16,  -1,  -1),
    ("multifamily",  16,    0,    2,    9,    10,  11,  12,  13,  -1,  14,  15,  -1,  -1),
]


def _try_variant(mfr_data: bytes, v):
    (label, total, cid_off, uid_s, uid_e, prod_off, blst_off, op_off,
     prot_off, pair_off, gen_off, ac_off, pan_off, lock_off) = v
    if cid_off + 1 >= len(mfr_data):
        return None
    if mfr_data[cid_off] != 0x56 or mfr_data[cid_off + 1] != 0x03:
        return None
    if prot_off >= len(mfr_data):
        return None
    if mfr_data[prot_off] not in (1, 2, 3):
        return None
    # Halo3 needs protocol byte == 3.
    if label == "halo3" and mfr_data[prot_off] != 3:
        return None
    if uid_e + 1 > len(mfr_data):
        return None

    data = {
        "variant": label,
        "unique_id_hex": mfr_data[uid_s:uid_e + 1].hex(),
        "product_id": mfr_data[prod_off] if prod_off < len(mfr_data) else None,
        "ble_status_info": mfr_data[blst_off] if blst_off < len(mfr_data) else None,
        "protocol_version": mfr_data[prot_off],
    }
    if op_off >= 0 and op_off < len(mfr_data):
        data["operating_mode"] = mfr_data[op_off]
    if pair_off >= 0 and pair_off < len(mfr_data):
        data["pairing_flag"] = mfr_data[pair_off]
    if gen_off < len(mfr_data):
        data["general_notification_index"] = mfr_data[gen_off]
    if ac_off < len(mfr_data):
        data["access_code_notification_index"] = mfr_data[ac_off]
    if pan_off >= 0 and pan_off < len(mfr_data):
        data["pan_discriminator"] = mfr_data[pan_off]
    if lock_off >= 0 and lock_off < len(mfr_data):
        data["lock_status_info"] = mfr_data[lock_off]
    return data


@register_parser(
    name="kwikset",
    company_id=SPECTRUM_COMPANY_ID,
    service_uuid=[LOCK_SYSTEM_UUID, ACTIVATION_UUID, SYSTEM_UUID, OTA_UUID],
    description="Kwikset / Spectrum Brands smart locks",
    version="1.0.0",
    core=False,
)
class KwiksetParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        metadata: dict = {}

        decoded = None
        if raw.manufacturer_data:
            for v in _VARIANTS:
                d = _try_variant(raw.manufacturer_data, v)
                if d:
                    decoded = d
                    break

        has_service_match = any(
            u.lower() in (LOCK_SYSTEM_UUID, ACTIVATION_UUID, SYSTEM_UUID, OTA_UUID)
            for u in (raw.service_uuids or [])
        )

        if decoded is None and not has_service_match:
            return None

        if decoded:
            metadata.update(decoded)
            id_basis = f"kwikset:{decoded['unique_id_hex']}"
        else:
            metadata["service_match"] = True
            id_basis = f"kwikset:{raw.mac_address}"

        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        raw_hex = raw.manufacturer_data.hex() if raw.manufacturer_data else ""

        return ParseResult(
            parser_name="kwikset",
            beacon_type="kwikset",
            device_class="lock",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )

    def storage_schema(self):
        return None
