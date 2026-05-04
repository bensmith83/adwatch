"""Roborock robot vacuum plugin.

Per apk-ble-hunting/reports/roborock-smart_passive.md. Two service UUIDs
distinguish lifecycle phase:

  - ``726F626F-C4EB-4040-963B-22076B601071`` — steady-state (paired to a
    user account, ready for BLE remote control)
  - ``726F626F-C4EB-4040-963B-22076B601051`` — factory-reset / Wi-Fi
    provisioning mode

The 128-bit UUID base ``726F626F-…`` starts with ASCII ``"robo"`` — a
cleartext vendor fingerprint visible in raw scan bytes.

Local name format: ``<vendor>-<modelSKU>_<deviceIdentifier>`` — the
device identifier is a stable per-device token used as identity-hash
basis (survives BLE MAC rotation).
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


ROBOROCK_STEADY_UUID = "726f626f-c4eb-4040-963b-22076b601071"
ROBOROCK_PROVISIONING_UUID = "726f626f-c4eb-4040-963b-22076b601051"

_NAME_RE = re.compile(r"^([a-zA-Z]+)-([A-Za-z0-9]+)_([A-Za-z0-9]+)$")


@register_parser(
    name="roborock",
    service_uuid=[ROBOROCK_STEADY_UUID, ROBOROCK_PROVISIONING_UUID],
    local_name_pattern=r"^roborock-",
    description="Roborock robot vacuum (steady + provisioning beacons)",
    version="1.0.0",
    core=False,
)
class RoborockParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        steady_hit = ROBOROCK_STEADY_UUID in normalized
        provisioning_hit = ROBOROCK_PROVISIONING_UUID in normalized

        local_name = raw.local_name or ""
        name_match = _NAME_RE.match(local_name)

        if not (steady_hit or provisioning_hit or name_match):
            return None

        metadata: dict = {"vendor": "Roborock"}

        if provisioning_hit:
            metadata["lifecycle"] = "provisioning"
            metadata["onboarded"] = False
        elif steady_hit:
            metadata["lifecycle"] = "steady_state"
            metadata["onboarded"] = True

        device_id: str | None = None
        if name_match:
            metadata["device_name"] = local_name
            metadata["model_token"] = name_match.group(2)
            device_id = name_match.group(3)
            metadata["device_identifier"] = device_id

        if device_id:
            id_basis = f"roborock:{device_id}"
        else:
            id_basis = f"roborock:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="roborock",
            beacon_type="roborock",
            device_class="vacuum",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
