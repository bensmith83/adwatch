"""Anki / DDL Vector robot plugin.

Per apk-ble-hunting/reports/anki-cozmo20_passive.md: Vector emits a
pairing-only advertisement using SIG-assigned 16-bit UUID 0xFEE3 and a
local name in the form ``Vector-XXXX`` where XXXX is the last 4 hex chars
of the robot's ESN (electronic serial number, printed in the battery bay).

There is no manufacturer-specific data and no service data. The fact that
a Vector is advertising at all means it is in pairing mode (back-button
double-tap), so presence of this beacon is itself a meaningful signal.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


VECTOR_SERVICE_UUID = "fee3"

_NAME_RE = re.compile(r"^Vector-([A-Z0-9]{4})$")


@register_parser(
    name="anki_vector",
    service_uuid=VECTOR_SERVICE_UUID,
    local_name_pattern=r"^Vector-[A-Z0-9]{4}$",
    description="Anki / DDL Vector robot (pairing-mode beacon)",
    version="1.0.0",
    core=False,
)
class AnkiVectorParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        uuid_hit = (
            VECTOR_SERVICE_UUID in normalized
            or any(u.endswith("0000fee3-0000-1000-8000-00805f9b34fb") for u in normalized)
        )

        local_name = raw.local_name or ""
        name_match = _NAME_RE.match(local_name)

        if not (uuid_hit or name_match):
            return None

        metadata: dict = {"vendor": "Anki", "product": "Vector"}
        esn_suffix: str | None = None

        if name_match:
            esn_suffix = name_match.group(1)
            metadata["esn_suffix"] = esn_suffix
            # Vector only advertises during the pairing window.
            metadata["pairing_mode"] = True
            metadata["device_name"] = local_name

        if esn_suffix is not None:
            id_basis = f"anki_vector:{esn_suffix}"
        else:
            id_basis = f"anki_vector:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        raw_hex = raw.manufacturer_data.hex() if raw.manufacturer_data else ""

        return ParseResult(
            parser_name="anki_vector",
            beacon_type="anki_vector",
            device_class="robot_toy",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )

    def storage_schema(self):
        return None
