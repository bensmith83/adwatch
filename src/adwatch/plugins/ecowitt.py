"""Ecowitt WS View plugin — provisioning-mode presence detection.

Ground truth: apk-ble-hunting report ``ecowitt-wsview_passive.md``
(``com.ost.wsview``, Stage 4b).

Ecowitt's BLE stack exists only to hand the console WiFi credentials.  The
advertisement carries a Complete Local Name (AD type ``0x09``) and, while the
console is in setup mode, the ``0xAAAA`` provisioning service UUID — nothing
else.  There is **no manufacturer data and no service data**: every weather
reading (temperature, humidity, soil, rain, wind, PM) reaches the gateway over
868/915 MHz Fine Offset RF and leaves it over WiFi.

So a visible Ecowitt advertiser is a useful *state* signal in its own right:
the console is unprovisioned or has been factory-reset, and during that window
the app ships the user's WiFi password in the clear over characteristic
``BBB0``.

``0xAAAA`` is an unassigned 16-bit UUID that cheap modules reuse freely, so it
is not registered as a match criterion — only the name is, with ``0xAAAA``
read afterwards as the provisioning-mode flag.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser, _normalize_uuid

# BluetoothFragment.java:922 post-filters on these name substrings; anchoring
# at the start keeps unrelated devices out.
ECOWITT_NAME_PATTERN = r"(?i)^(WS19|HP10|AMBWeather)"

_ECOWITT_NAME_RE = re.compile(ECOWITT_NAME_PATTERN)

# Provisioning GATT service, advertised only while in setup mode.
PROVISIONING_UUID = "aaaa"
_PROVISIONING_UUID_FULL = _normalize_uuid(PROVISIONING_UUID)

# Longest first so WS1950 is not swallowed by the WS19 family fallback.
MODEL_FAMILIES = ("AMBWEATHER", "WS1950", "WS1900", "HP10", "WS19")


@register_parser(
    name="ecowitt",
    local_name_pattern=ECOWITT_NAME_PATTERN,
    description="Ecowitt / Ambient Weather consoles in BLE provisioning mode",
    version="1.0.0",
    core=False,
)
class EcowittParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        name = raw.local_name
        if not name or not _ECOWITT_NAME_RE.search(name):
            return None

        metadata: dict = {
            "local_name": name,
            "model_family": self._model_family(name),
            # All sensor data goes out over WiFi, never over BLE.
            "telemetry": False,
            "provisioning_mode": self._is_provisioning(raw),
        }

        id_hash = hashlib.sha256(
            f"ecowitt:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="ecowitt",
            beacon_type="ecowitt",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )

    @staticmethod
    def _model_family(name: str) -> str:
        upper = name.upper()
        for family in MODEL_FAMILIES:
            if upper.startswith(family):
                # Report the vendor's own casing for the rebrand.
                return "AMBWeather" if family == "AMBWEATHER" else family
        return "unknown"

    @staticmethod
    def _is_provisioning(raw: RawAdvertisement) -> bool:
        for uuid in (raw.service_uuids or []):
            if _normalize_uuid(uuid) == _PROVISIONING_UUID_FULL:
                return True
        for key in (raw.service_data or {}):
            if _normalize_uuid(key) == _PROVISIONING_UUID_FULL:
                return True
        return False
