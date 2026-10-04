"""NOWATCH screenless EDA / stress wearable plugin.

Per apk-ble-hunting/reports/nowatch-app_passive.md: the advertised name is
``NOWATCH <model><serial>`` (e.g. ``NOWATCH MB2900897``). The app strips the
``NOWATCH `` prefix and uses the suffix verbatim as the device handle, so it
is a stable per-unit identifier. No telemetry is advertised.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


NOWATCH_NAME_PATTERN = r"^NOWATCH"
NOWATCH_NAME_PREFIX = "NOWATCH "
_MODEL_SERIAL_RE = re.compile(r"^([A-Z]+)(\d+)$")


@register_parser(
    name="nowatch",
    local_name_pattern=NOWATCH_NAME_PATTERN,
    description="NOWATCH EDA stress wearable (name-embedded unit id)",
    version="1.0.0",
    core=False,
)
class NowatchParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        name = raw.local_name or ""
        if not name.startswith("NOWATCH"):
            return None

        metadata: dict = {
            "vendor": "NOWATCH",
            "product": "NOWATCH EDA wearable",
            "device_name": name,
            "telemetry": "none (post-connect GATT only)",
            "sensitive": True,
            "sensitive_category": "mental_health",
        }

        unit_id = name[len(NOWATCH_NAME_PREFIX):].strip() if name.startswith(NOWATCH_NAME_PREFIX) else ""
        if unit_id:
            metadata["unit_id"] = unit_id
            m = _MODEL_SERIAL_RE.match(unit_id)
            if m:
                metadata["model_code"] = m.group(1)
                metadata["serial"] = m.group(2)
            basis = f"nowatch:{unit_id}"
        else:
            basis = f"nowatch:{raw.mac_address}"

        id_hash = hashlib.sha256(basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="nowatch",
            beacon_type="nowatch",
            device_class="wearable",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
