"""Nanoleaf HomeKit / mfr-data plugin.

Per apk-ble-hunting/reports/nanoleaf-nanoleaf_passive.md:

  - Apple HAP advertisement under company ID 0x004C with first payload
    byte = 0x06 (HAP AD type).
  - Nanoleaf-branded mfr-data under company ID 0x080B (2059, Nanoleaf).
  - Names: ^(Shapes|Canvas|NLM\\d|NL1D|Nanoleaf)

The HAP advertisement carries:
  - 6-byte Accessory Advertising Identifier (AAI) — stable per-pairing,
    survives BLE address rotation.
  - 2-byte Global State Number (GSN) — bumps on every HomeKit state change.
  - 2-byte HAP category (0x0005 = Lightbulb).
  - 1-byte status flags (bit 0 = paired/discoverable).
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


APPLE_COMPANY_ID = 0x004C
NANOLEAF_COMPANY_ID = 0x080B
HAP_AD_TYPE = 0x06

# HAP category enum (subset relevant to Nanoleaf).
HAP_CATEGORIES = {
    0x0005: "Lightbulb",
    0x000C: "Sensor",
    0x000D: "Switch",
}


def _parse_hap_advert(payload: bytes) -> dict | None:
    """Decode a HAP advertisement payload (post-CID strip).

    Layout per HAP R14 § 7.4.2.2:
        [0]   AD type (0x06)
        [1]   length (low 5 bits) + AD version (high 3 bits)
        [2-3] HAP category (uint16 LE)
        [4-5] Global State Number (uint16 LE)
        [6-11] Accessory Advertising Identifier (6 bytes)
        [12]  Accessory Config Number
        [13]  Compatible Version
    """
    if not payload or len(payload) < 14 or payload[0] != HAP_AD_TYPE:
        return None
    md: dict = {}
    md["hap_ad_version"] = (payload[1] >> 5) & 0x07
    md["hap_length"] = payload[1] & 0x1F
    cat = int.from_bytes(payload[2:4], "little")
    md["hap_category_code"] = cat
    md["hap_category"] = HAP_CATEGORIES.get(cat, f"unknown_{cat}")
    md["hap_gsn"] = int.from_bytes(payload[4:6], "little")
    md["hap_aai"] = ":".join(f"{b:02X}" for b in payload[6:12])
    md["hap_config_number"] = payload[12]
    md["hap_compatible_version"] = payload[13]
    # Status flags live in byte 1's low bits per some Apple variants — we
    # don't decode further to avoid spec drift.
    return md


@register_parser(
    name="nanoleaf",
    company_id=(APPLE_COMPANY_ID, NANOLEAF_COMPANY_ID),
    local_name_pattern=r"^(Shapes|Canvas|NLM\d|NL1D|Nanoleaf)",
    description="Nanoleaf Shapes/Canvas/Essentials (HomeKit + Nanoleaf mfr-data)",
    version="1.0.0",
    core=False,
)
class NanoleafParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        cid = raw.company_id
        payload = raw.manufacturer_payload
        name = raw.local_name or ""
        name_hit = bool(name and (
            name.startswith("Shapes") or name.startswith("Canvas")
            or name.startswith("NLM") or name.startswith("NL1D")
            or name.startswith("Nanoleaf")
        ))

        # CID gates — Nanoleaf strictly, or Apple+HAP-byte for HomeKit.
        nano_cid_hit = cid == NANOLEAF_COMPANY_ID
        apple_hap_hit = (
            cid == APPLE_COMPANY_ID and payload is not None and len(payload) >= 1
            and payload[0] == HAP_AD_TYPE
        )

        # Name alone isn't enough to claim ownership of an Apple HAP advert
        # — restrict to actual Nanoleaf signals or unambiguous Nanoleaf names.
        if not (nano_cid_hit or apple_hap_hit or name_hit):
            return None

        metadata: dict = {}

        if nano_cid_hit:
            metadata["nanoleaf_mfr_present"] = True
            if payload:
                metadata["nanoleaf_payload_hex"] = payload.hex()

        if apple_hap_hit:
            hap = _parse_hap_advert(payload)
            if hap:
                metadata.update(hap)
                metadata["homekit_paired"] = bool(payload[1] & 0x01) is False

        if name:
            metadata["device_name"] = name
            # Family classification.
            if name.startswith("Shapes"):
                metadata["model_family"] = "Shapes"
            elif name.startswith("Canvas"):
                metadata["model_family"] = "Canvas"
            elif name.startswith("NLM"):
                metadata["model_family"] = "Essentials"
            elif name.startswith("NL1D"):
                metadata["model_family"] = "NL1D"
            elif name.startswith("Nanoleaf"):
                metadata["model_family"] = "Aurora"

        # Identity prefers the stable AAI (HAP) when available.
        aai = metadata.get("hap_aai")
        if aai:
            id_basis = f"nanoleaf:{aai}"
        else:
            id_basis = f"nanoleaf:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        raw_hex = payload.hex() if payload else ""

        return ParseResult(
            parser_name="nanoleaf",
            beacon_type="nanoleaf",
            device_class="light",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )

    def storage_schema(self):
        return None
