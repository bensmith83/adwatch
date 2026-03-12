"""Vendor lookup for BLE advertisements.

Two sources:
- Bluetooth SIG company IDs (from manufacturer_data first 2 bytes)
- IEEE OUI prefixes (from MAC address first 3 bytes)
"""

from __future__ import annotations

from adwatch._bt_company_ids import BT_COMPANY_IDS
from adwatch._oui_vendors import OUI_VENDORS


def bt_company_name(company_id: int | None) -> str | None:
    """Look up Bluetooth SIG company name by company ID."""
    if company_id is None:
        return None
    return BT_COMPANY_IDS.get(company_id)


def oui_vendor(mac: str | None) -> str | None:
    """Look up IEEE OUI vendor by MAC address prefix."""
    if not mac or len(mac) < 8:
        return None
    prefix = mac[:8].upper().replace(":", "")
    return OUI_VENDORS.get(prefix)


def best_vendor(
    mac: str | None,
    address_type: str | None,
    company_id: int | None,
) -> str | None:
    """Best-guess vendor: prefer BT SIG company ID, fall back to OUI for public MACs."""
    bt = bt_company_name(company_id)
    if bt:
        return bt
    if address_type and "random" in address_type:
        return None
    return oui_vendor(mac)
