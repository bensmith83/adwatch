"""Huami Mi Band / Amazfit / Zepp wearable plugin.

Per apk-ble-hunting/reports/xiaomi-hm-health_passive.md. Two service UUID
generations distinguish product lines:

  - **Mi Band 1-3** (legacy) — service UUID ``0x0000FEE0``
  - **Mi Band 4+ / Amazfit (Bip / GTR / GTS / T-Rex / Stratos / Verge)** —
    service UUID ``0000FED0-0000-3512-2118-0009AF100700`` (Huami-proprietary
    base)

Plus name patterns covering ``MI Band``, ``Mi Smart Band``, ``Amazfit``,
``Zepp``. The Mi Scale path (service-data ``0x181B`` / ``0x181D``) is
already handled by ``plugins/mi_scale.py``.

Zepp / Amazfit watches additionally broadcast a Huami **extended
advertisement** under company ID ``0x0157`` — per
apk-ble-hunting/reports/huami-watch-hmwatchmanager_passive.md
(``ManufacturerAdvDataParserKt.c()``).  Offsets below are within
``RawAdvertisement.manufacturer_payload`` (the report's offsets minus the
2-byte company ID):

    0        format selector, must be 0x02
    1..      sub-TLVs ``[length:u8][type:u8][value:length-1]``
             type 0x01 → heart rate (uint8 BPM)
             type 0x02 → charging state (bool)
             type 0x03 → account-bound state (bool)
    -7       filler byte
    -6..-1   6-byte hardware address, kept separately from the BLE MAC

That makes live heart rate, charger state and Zepp-account binding readable
without connecting, and the hardware address a persistent per-unit
identifier that survives BLE MAC rotation — so it is preferred as the
identity basis.  Mi Band 1-3 legacy advertisements remain presence-only:
their HR/steps/sleep telemetry needs a post-connect authenticated session
(Huami AES-128 challenge-response).

Note: ``plugins/renpho.py`` also registers company ID ``0x0157`` for
Qingniu-OEM scales (Qingniu is Huami's scale arm and shares the SIG
registration).  The decode here is gated on the ``0x02`` format selector so
it never claims a scale advertisement.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


MIBAND_LEGACY_UUID = "0000fee0-0000-1000-8000-00805f9b34fb"
HUAMI_NEW_UUID = "0000fed0-0000-3512-2118-0009af100700"

# Anhui Huami Information Technology Co., Ltd. (343).
HUAMI_COMPANY_ID = 0x0157

# manufacturer_payload[0] selecting the extended-advertisement format.
EXTENDED_ADV_PREFIX = 0x02

TLV_HEART_RATE = 0x01
TLV_CHARGING = 0x02
TLV_BOUND = 0x03

# filler byte + 6-byte hardware address at the end of the payload.
_TRAILER_LEN = 7

_SHORT_LEGACY = "fee0"

_NAME_RE = re.compile(r"^(MI Band|Mi Smart Band|Amazfit|Zepp)\s*(.+)?$")


def _decode_extended_adv(payload: bytes) -> dict:
    """Decode the Huami extended-advertisement TLVs plus hardware address."""
    metadata: dict = {"adv_format": "extended"}

    # The trailer is fixed-width, so reserve it before walking the TLVs —
    # a non-zero filler byte would otherwise be read as a TLV length.
    if len(payload) >= _TRAILER_LEN + 1:
        trailer_start = len(payload) - _TRAILER_LEN
        metadata["hardware_address"] = ":".join(
            f"{b:02X}" for b in payload[trailer_start + 1:]
        )
    else:
        trailer_start = len(payload)

    cur = 1
    while cur + 2 <= trailer_start:
        length = payload[cur]
        if length == 0:
            break
        if cur + 1 + length > trailer_start:
            break
        tlv_type = payload[cur + 1]
        value = payload[cur + 2:cur + 1 + length]
        if value:
            if tlv_type == TLV_HEART_RATE:
                metadata["heart_rate"] = value[0]
            elif tlv_type == TLV_CHARGING:
                metadata["charging"] = value[0] != 0
            elif tlv_type == TLV_BOUND:
                metadata["account_bound"] = value[0] != 0
        cur += 1 + length

    return metadata


@register_parser(
    name="huami_amazfit",
    company_id=HUAMI_COMPANY_ID,
    service_uuid=[MIBAND_LEGACY_UUID, HUAMI_NEW_UUID],
    local_name_pattern=r"^(MI Band|Mi Smart Band|Amazfit|Zepp)",
    description="Huami / Amazfit / Mi Band wearables",
    version="1.1.0",
    core=False,
)
class HuamiAmazfitParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        legacy_hit = MIBAND_LEGACY_UUID in normalized or _SHORT_LEGACY in normalized
        new_hit = HUAMI_NEW_UUID in normalized

        local_name = raw.local_name or ""
        name_match = _NAME_RE.match(local_name)

        cid_hit = raw.company_id == HUAMI_COMPANY_ID

        if not (legacy_hit or new_hit or name_match or cid_hit):
            return None

        metadata: dict = {"vendor": "Huami"}

        if legacy_hit:
            metadata["product_family"] = "mi_band_legacy"
        elif new_hit:
            metadata["product_family"] = "huami_new"
        elif name_match:
            # Name-only fallback — be conservative.
            tag = name_match.group(1)
            metadata["product_family"] = (
                "mi_band_legacy" if tag.startswith("MI Band") else "huami_new"
            )
        else:
            # Manufacturer-data-only: the watches advertise no recognizable
            # service UUID at all.
            metadata["product_family"] = "huami_watch"

        if name_match:
            metadata["device_name"] = local_name
            tag = name_match.group(1)
            tail = (name_match.group(2) or "").strip()
            if tag == "Mi Smart Band":
                metadata["model_hint"] = f"Smart Band {tail}".strip()
            elif tag == "MI Band":
                metadata["model_hint"] = f"Band {tail}".strip()
            elif tail:
                metadata["model_hint"] = tail

        payload = raw.manufacturer_payload if cid_hit else None
        if payload and payload[0] == EXTENDED_ADV_PREFIX:
            metadata.update(_decode_extended_adv(payload))

        # The advertised hardware address is stored separately from the BLE
        # MAC and does not rotate, so it is the better identity basis.
        hardware_address = metadata.get("hardware_address")
        id_basis = f"huami_amazfit:{hardware_address or raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="huami_amazfit",
            beacon_type="huami_amazfit",
            device_class="wearable",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
