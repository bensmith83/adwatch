"""Core dataclasses for adwatch."""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

_BT_BASE_RE = re.compile(r"^0000([0-9a-f]{4})-0000-1000-8000-00805f9b34fb$", re.I)


def deserialize_service_data(svc_json_str: str) -> dict[str, bytes]:
    """Deserialize service_data_json from DB, adding short UUID aliases.

    The DB stores full UUIDs (e.g. '0000fe9a-0000-1000-8000-00805f9b34fb')
    but parsers look up by short UUID ('fe9a'). This adds both forms.
    """
    import json
    svc_map = json.loads(svc_json_str)
    result: dict[str, bytes] = {}
    for k, v in svc_map.items():
        data = bytes.fromhex(v)
        result[k] = data
        m = _BT_BASE_RE.match(k)
        if m:
            result[m.group(1)] = data
    return result


def classify_mac_type(address_type: str, mac_address: str) -> str:
    """Classify BLE MAC address into one of four types.

    - public: Programmed by manufacturer, registered with IEEE
    - random_static: Configurable at boot, fixed through device lifetime
    - resolvable_private: Changes periodically, resolvable via IRK
    - non_resolvable_private: Changes periodically, not resolvable
    - reserved: Top 2 bits = 10 (not defined in BLE spec)
    """
    if address_type.lower() == "public":
        return "public"
    first_byte = int(mac_address.split(":")[0], 16)
    top_bits = (first_byte >> 6) & 0x03
    if top_bits == 0b11:
        return "random_static"
    elif top_bits == 0b01:
        return "resolvable_private"
    elif top_bits == 0b00:
        return "non_resolvable_private"
    else:  # 0b10
        return "reserved"


@dataclass
class RawAdvertisement:
    """A single BLE advertisement as received from the scanner."""
    timestamp: str  # ISO 8601
    mac_address: str  # BLE MAC (may be random)
    address_type: str  # "public" or "random"
    manufacturer_data: bytes | None  # Full manufacturer data (company_id + payload)
    service_data: dict[str, bytes] | None  # UUID -> data mapping
    service_uuids: list[str] = field(default_factory=list)
    local_name: str | None = None
    rssi: int = -100
    tx_power: int | None = None

    @classmethod
    def now(cls, **kwargs) -> "RawAdvertisement":
        """Create a RawAdvertisement with current timestamp."""
        kwargs.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        kwargs.setdefault("address_type", "random")
        return cls(**kwargs)

    @property
    def mac_type(self) -> str:
        """Classify the MAC address type based on address_type and MAC MSBs."""
        return classify_mac_type(self.address_type, self.mac_address)

    @property
    def company_id(self) -> int | None:
        """Extract 2-byte company ID from manufacturer_data (little-endian)."""
        if self.manufacturer_data and len(self.manufacturer_data) >= 2:
            return int.from_bytes(self.manufacturer_data[:2], "little")
        return None

    @property
    def manufacturer_payload(self) -> bytes | None:
        """Manufacturer data without the company ID prefix."""
        if self.manufacturer_data and len(self.manufacturer_data) > 2:
            return self.manufacturer_data[2:]
        return None


@dataclass
class Classification:
    """Broad classification of a BLE advertisement."""
    ad_type: str  # e.g. "apple_nearby", "samsung_ble", "thermopro"
    ad_category: str  # e.g. "phone", "speaker", "sensor", "tracker"
    source: str  # "company_id", "service_uuid", "local_name"


@dataclass
class ParseResult:
    """Standard output format from all parsers."""
    parser_name: str  # e.g. "thermopro", "apple_continuity"
    beacon_type: str  # e.g. "thermopro", "apple_nearby"
    device_class: str  # e.g. "sensor", "phone", "tracker"
    identifier_hash: str  # SHA256-based stable ID (16 hex chars)
    raw_payload_hex: str  # Hex-encoded matched payload
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)
    event_type: str | None = None  # WebSocket event name
    storage_table: str | None = None  # Table name for parsed storage
    storage_row: dict | None = None  # Column->value for parsed storage insert
    stable_key: str | None = None  # Stable dedup key (replaces volatile payload in signature)


@dataclass
class PluginUIConfig:
    """Frontend tab/widget configuration for a plugin."""
    tab_name: str
    tab_icon: str | None = None
    widgets: list["WidgetConfig"] = field(default_factory=list)
    refresh_interval: int = 0  # Auto-refresh seconds (0 = WebSocket only)


@dataclass
class WidgetConfig:
    """Configuration for a single UI widget."""
    widget_type: str  # "summary_card", "data_table", "time_chart", etc.
    title: str
    data_endpoint: str  # API endpoint to fetch data from
    config: dict = field(default_factory=dict)
    render_hints: dict = field(default_factory=dict)
