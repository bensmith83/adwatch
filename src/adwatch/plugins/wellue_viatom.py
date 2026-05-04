"""Wellue / Viatom / Vtrump (Shenzhen Lepu Medical) plugin.

Per apk-ble-hunting/reports/viatom-vihealth_passive.md:

  - 226-device name catalog matched by substring (`str.contains`).
  - Wellue custom service UUIDs (81EEA001 / A149B001).
  - Vtrump scale UUIDs (F433BD80, 6E40FC00, 78667579 family).
  - MAC OUI fingerprints `:4D:57` and `:56:10`.

Name-only discovery — no rich mfr-data parsing in the app. We classify by
substring against a curated subset of the 226-name catalog (the most
discriminative product-class prefixes).
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


WELLUE_PRIMARY_UUID = "81eea001-e735-49ec-8a11-7e32cae1e14e"
WELLUE_SECONDARY_UUID = "a149b001-fd80-47c2-a5e1-cb26b44667a7"
VTRUMP_SCALE_UUID = "f433bd80-75b8-11e2-97d9-0002a5d5c51b"
VTRUMP_NORDIC_UUID = "6e40fc00-b5a3-f393-e0a9-e50e24dcca9e"
VTRUMP_CONFIG_UUID = "78667579-0e7c-45ac-bb53-5279f8ee16fc"
VTRUMP_IBEACON_UUID = "78667579-1149-4499-9e54-52e4e761ccd9"

WELLUE_SERVICE_UUIDS = (
    WELLUE_PRIMARY_UUID, WELLUE_SECONDARY_UUID,
    VTRUMP_SCALE_UUID, VTRUMP_NORDIC_UUID,
    VTRUMP_CONFIG_UUID, VTRUMP_IBEACON_UUID,
)

# OUI suffixes flagged in the app for early MAC-based classification.
_OUI_SUFFIXES = (":4D:57", ":56:10")

# Name-substring → product-class table. Substring matching per the app's logic
# (`str.contains`). Most-specific substrings first to avoid mis-classification.
NAME_RULES = [
    ("FHR-666(BLE)", "fetal_heart_rate_doppler"),
    ("DuoEK", "portable_ecg"),
    ("Checkme", "vitals_monitor"),
    ("KidsO2", "pediatric_pulse_oximeter"),
    ("BabyO2", "pediatric_pulse_oximeter"),
    ("O2Ring", "continuous_pulse_oximeter_ring"),
    ("OxyU", "wearable_pulse_oximeter"),
    ("OxyRing", "wearable_pulse_oximeter"),
    ("OxyFit", "wearable_pulse_oximeter"),
    ("Oxylink", "wearable_pulse_oximeter"),
    ("OxySmart", "wearable_pulse_oximeter"),
    ("Oxyfit", "wearable_pulse_oximeter"),
    ("LEPU-ER", "ecg_patch"),
    ("LP ER", "ecg_patch"),
    ("ER1", "ecg_patch"),
    ("ER2", "ecg_patch"),
    ("ER3", "ecg_patch"),
    ("VBeat", "ecg_patch"),
    ("BP2", "blood_pressure_monitor"),
    ("BP3", "blood_pressure_monitor"),
    ("Bioland-BGM", "blood_glucose_monitor"),
    ("Lescale", "smart_scale"),
    ("Le S", "smart_scale"),
    ("le B", "smart_scale"),
    ("MY_SCALE", "smart_scale"),
    ("BBSM", "oem_rebrand"),
    ("BUZUD", "oem_rebrand"),
    ("Aura_BP", "oem_rebrand"),
    ("SI PO", "oem_rebrand"),
    ("Viatom", "vitals_monitor"),
    ("PC-60", "pulse_oximeter"),
    ("PC80B", "ecg_handheld"),
    ("AOJ-20A", "thermometer"),
    ("AP-20", "thermometer"),
    ("T31", "thermometer"),
    ("PM10", "specialty_sensor"),
    ("POD-1", "vitals_pod"),
    ("POD-2B", "vitals_pod"),
]

_NAME_REGEX = re.compile(
    r"(?i)(FHR-666|DuoEK|Checkme|KidsO2|BabyO2|O2Ring|OxyU|OxyRing|OxyFit|"
    r"Oxylink|OxySmart|Oxyfit|LEPU-ER|LP ER|ER1|ER2|ER3|VBeat|BP2|BP3|"
    r"Bioland|Lescale|MY_SCALE|BBSM|BUZUD|Aura_BP|SI PO|Viatom|PC-60|PC80B|"
    r"AOJ-20A|AP-20|T31|PM10|POD-1|POD-2B)"
)


@register_parser(
    name="wellue_viatom",
    service_uuid=WELLUE_SERVICE_UUIDS,
    local_name_pattern=_NAME_REGEX.pattern,
    description="Wellue / Viatom / Vtrump (Shenzhen Lepu Medical) ecosystem",
    version="1.0.0",
    core=False,
)
class WellueViatomParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        uuid_hits = [u for u in WELLUE_SERVICE_UUIDS if u in normalized]
        oui_hit = any(raw.mac_address.upper().endswith(s) for s in _OUI_SUFFIXES)
        name = raw.local_name or ""

        # Find matching product class by substring scan against catalog.
        product_class = None
        match_substring = None
        for substring, klass in NAME_RULES:
            if substring.lower() in name.lower():
                product_class = klass
                match_substring = substring
                break

        if not (uuid_hits or oui_hit or product_class):
            return None

        metadata: dict = {}
        if product_class:
            metadata["product_class"] = product_class
            metadata["matched_substring"] = match_substring
            metadata["device_name"] = name
        if uuid_hits:
            metadata["matched_service_uuids"] = uuid_hits
            if VTRUMP_IBEACON_UUID in uuid_hits:
                metadata["vtrump_ibeacon_mode"] = True
        if oui_hit:
            metadata["wellue_oui_hit"] = True

        id_hash = hashlib.sha256(
            f"wellue:{raw.mac_address}:{name}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="wellue_viatom",
            beacon_type="wellue_viatom",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
