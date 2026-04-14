"""Broad advertisement classifier — lookup-table-based classification."""

from __future__ import annotations

import re

from adwatch.models import RawAdvertisement, Classification


# ---------------------------------------------------------------------------
# Company ID registry: company_id (int) -> (ad_type, ad_category)
# ---------------------------------------------------------------------------

COMPANY_ID_REGISTRY: dict[int, tuple[str, str]] = {
    0x004C: ("apple", "phone"),
    0x0075: ("samsung", "phone"),
    0x0006: ("microsoft", "computer"),
    0x00E0: ("google", "phone"),
    0x038F: ("xiaomi", "phone"),
    0x05A7: ("sonos", "speaker"),
    0x0065: ("bose", "audio"),
    0x0434: ("hatch", "smart_home"),
    0xEC88: ("govee", "sensor"),
    0xEF88: ("govee", "sensor"),
}


# ---------------------------------------------------------------------------
# Apple subtype registry: TLV type byte -> (ad_type, ad_category)
# ---------------------------------------------------------------------------

APPLE_SUBTYPE_REGISTRY: dict[int, tuple[str, str]] = {
    0x02: ("ibeacon", "beacon"),
    0x05: ("apple_airdrop", "phone"),
    0x06: ("apple_homekit", "iot"),
    0x07: ("apple_proximity", "accessory"),
    0x08: ("apple_siri", "phone"),
    0x09: ("apple_airplay", "media"),
    0x0B: ("apple_magic_switch", "phone"),
    0x0C: ("apple_handoff", "phone"),
    0x0D: ("apple_tethering", "phone"),
    0x0E: ("apple_tethering_source", "phone"),
    0x0F: ("apple_nearby_action", "phone"),
    0x10: ("apple_nearby", "phone"),
    0x12: ("apple_findmy", "tracker"),
}


# ---------------------------------------------------------------------------
# Service UUID registry: UUID string -> (ad_type, ad_category)
# Keys stored in lowercase full 128-bit form for consistent matching.
# ---------------------------------------------------------------------------

SERVICE_UUID_REGISTRY: dict[str, tuple[str, str]] = {
    "0000fe2c-0000-1000-8000-00805f9b34fb": ("fast_pair", "accessory"),
    "0000fff6-0000-1000-8000-00805f9b34fb": ("matter", "smart_home"),
    "0000feed-0000-1000-8000-00805f9b34fb": ("tile", "tracker"),
    "0000fd5a-0000-1000-8000-00805f9b34fb": ("smarttag", "tracker"),
    "0000feaf-0000-1000-8000-00805f9b34fb": ("nest", "smart_home"),
    "0000fe9a-0000-1000-8000-00805f9b34fb": ("estimote", "beacon"),
    "00003081-0000-1000-8000-00805f9b34fb": ("flipper", "tool"),
}


# ---------------------------------------------------------------------------
# Local name patterns: list of (regex_str, ad_type, ad_category)
# ---------------------------------------------------------------------------

LOCAL_NAME_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"^TP\d{3}"), "thermopro", "sensor"),
    (re.compile(r"iPhone"), "apple", "phone"),
    (re.compile(r"^Sonos\b"), "sonos", "speaker"),
    (re.compile(r"Flipper"), "flipper", "tool"),
    (re.compile(r"Hatch"), "hatch", "smart_home"),
    (re.compile(r"^GV(H5|5124)"), "govee", "sensor"),
    (re.compile(r"^KS03~[0-9a-fA-F]{6}$"), "ks03_hid_remote", "remote"),
]


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

class Classifier:
    """Broad BLE advertisement classifier using lookup tables."""

    def classify(self, raw: RawAdvertisement) -> Classification | None:
        """Classify an advertisement. Priority: company_id > service_uuid > local_name."""

        # 1. Company ID
        result = self._classify_company_id(raw)
        if result is not None:
            return result

        # 2. Service UUID
        result = self._classify_service_uuid(raw)
        if result is not None:
            return result

        # 3. Local name
        result = self._classify_local_name(raw)
        if result is not None:
            return result

        return None

    def _classify_company_id(self, raw: RawAdvertisement) -> Classification | None:
        company_id = raw.company_id
        if company_id is None:
            return None

        if company_id not in COMPANY_ID_REGISTRY:
            return None

        # Special handling for Apple: check subtypes
        if company_id == 0x004C:
            payload = raw.manufacturer_payload
            if payload and len(payload) >= 1:
                subtype = payload[0]
                if subtype in APPLE_SUBTYPE_REGISTRY:
                    ad_type, ad_category = APPLE_SUBTYPE_REGISTRY[subtype]
                    return Classification(ad_type=ad_type, ad_category=ad_category, source="company_id")
            # Fall back to generic Apple
            ad_type, ad_category = COMPANY_ID_REGISTRY[0x004C]
            return Classification(ad_type=ad_type, ad_category=ad_category, source="company_id")

        ad_type, ad_category = COMPANY_ID_REGISTRY[company_id]
        return Classification(ad_type=ad_type, ad_category=ad_category, source="company_id")

    def _classify_service_uuid(self, raw: RawAdvertisement) -> Classification | None:
        for uuid in raw.service_uuids:
            key = uuid.lower()
            if key in SERVICE_UUID_REGISTRY:
                ad_type, ad_category = SERVICE_UUID_REGISTRY[key]
                return Classification(ad_type=ad_type, ad_category=ad_category, source="service_uuid")
        return None

    def _classify_local_name(self, raw: RawAdvertisement) -> Classification | None:
        if not raw.local_name:
            return None
        for pattern, ad_type, ad_category in LOCAL_NAME_PATTERNS:
            if pattern.search(raw.local_name):
                return Classification(ad_type=ad_type, ad_category=ad_category, source="local_name")
        return None
