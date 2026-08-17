"""RingConn smart-ring BLE plugin.

Per apk-ble-hunting/reports/gdjztech-ringconn_passive.md (app
``com.gdjztech.ringconn``, Flutter/Dart AOT).

The app discovers the ring purely by advertised-name keyword — its Dart image
wires up ``flutter_blue_plus``'s ``withKeywords`` filter and none of
``withServices`` / ``withServiceData`` / ``withMsd``.  So detection here is
name-only:

  - The advertised name is the constant ``RingConn``, identical across units,
    so it is a **product** fingerprint, not a unique-device one.  Any trailing
    suffix is captured as ``name_suffix`` in case firmware appends one — the
    report could not rule that out statically.
  - Per-device disambiguation in the app is done by stored MAC, which is what
    the identity hash falls back to.

No passive telemetry exists: health data travels over the Nordic UART service
after a connect-time handshake and is AES-GCM wrapped.  The NUS UUID is
generic and only present post-connect, so it is deliberately not a matcher.

Not to be confused with the app's "RingConn ID" — that is a cloud/social
account identifier for the friend feature, never an over-the-air field.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

# \b keeps "RingConnector" and similar words out while still allowing a
# hyphen/space-separated hardware suffix.
RINGCONN_NAME_PATTERN = r"^RingConn\b"

_RINGCONN_RE = re.compile(r"^RingConn\b[\s_-]*(.*)$")


@register_parser(
    name="ringconn",
    local_name_pattern=RINGCONN_NAME_PATTERN,
    description="RingConn smart ring advertisements",
    version="1.0.0",
    core=False,
)
class RingConnParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.local_name:
            return None
        match = _RINGCONN_RE.match(raw.local_name)
        if not match:
            return None

        metadata: dict = {
            "vendor": "RingConn",
            "product": "smart ring",
            "device_name": raw.local_name,
            # The advertised name is constant across units.
            "name_is_unique": False,
        }

        suffix = match.group(1).strip()
        if suffix:
            metadata["name_suffix"] = suffix

        id_hash = hashlib.sha256(
            f"ringconn:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="ringconn",
            beacon_type="ringconn",
            device_class="wearable",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
