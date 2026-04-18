"""ecobee smart home device BLE advertisement parser.

Per apk-ble-hunting/reports/ecobee-athenamobile_passive.md. Devices advertise
`ecobee Inc. - <serial>` only during WiFi provisioning. Serial prefix encodes
product family (61/63 = thermostat/sensor/etc., 71 = camera, 72 = contact).
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


_ECOBEE_NAME_RE = re.compile(r"^ecobee Inc\. - (\d{9,12})$")

_SERIAL_PREFIX_MAP = {
    "61": "thermostat/sensor family",
    "63": "thermostat/sensor family",
    "71": "camera (THEIA)",
    "72": "contact sensor (HECATE)",
}


@register_parser(
    name="ecobee",
    local_name_pattern=r"^ecobee Inc\. - ",
    description="ecobee smart thermostats, sensors, and cameras (provisioning)",
    version="1.0.0",
    core=False,
)
class EcobeeParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        name = raw.local_name or ""
        m = _ECOBEE_NAME_RE.match(name)
        if not m:
            return None

        serial = m.group(1)
        prefix = serial[:2]

        metadata: dict = {
            "device_name": name,
            "serial": serial,
            "serial_prefix": prefix,
            "product_family": _SERIAL_PREFIX_MAP.get(prefix, "unknown"),
            "provisioning_mode": True,
        }

        id_hash = hashlib.sha256(f"ecobee:{serial}".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="ecobee",
            beacon_type="ecobee",
            device_class="smart_home",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
