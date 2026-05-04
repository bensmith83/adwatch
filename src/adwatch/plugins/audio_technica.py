"""Audio-Technica Connect plugin.

Per apk-ble-hunting/reports/audiotechnica-connect_passive.md:

  - Qualcomm GAIA service UUID 00001100-d102-11e1-9b23-00025b00a5a5
    (shared across CSR-based products — not AT-exclusive).
  - AT-proprietary Airoha UUID DC7783C4-2950-4142-AD46-07A9889584D9
    (strong AT fingerprint).
  - Name prefix `ATH-` (Classic BT mostly; sometimes BLE).

BLE-adv presence is sparse — most ATH devices are bonded BR/EDR with BLE
only for RSSI scans and OTA. Identification is presence-only.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


GAIA_BLE_UUID = "00001100-d102-11e1-9b23-00025b00a5a5"
AT_AIROHA_UUID = "dc7783c4-2950-4142-ad46-07a9889584d9"

_NAME_RE = re.compile(r"^ATH-")


@register_parser(
    name="audio_technica",
    service_uuid=AT_AIROHA_UUID,
    local_name_pattern=r"^ATH-",
    description="Audio-Technica headphones (Airoha + name)",
    version="1.0.0",
    core=False,
)
class AudioTechnicaParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        airoha_hit = AT_AIROHA_UUID in normalized
        gaia_hit = GAIA_BLE_UUID in normalized
        name_match = _NAME_RE.match(raw.local_name) if raw.local_name else None

        if not (airoha_hit or name_match):
            return None

        metadata: dict = {"vendor": "Audio-Technica"}

        if airoha_hit:
            metadata["chipset_family"] = "airoha"
        elif name_match and gaia_hit:
            metadata["chipset_family"] = "qualcomm_qcc"
        elif name_match:
            metadata["chipset_family"] = "unknown"

        if name_match and raw.local_name:
            metadata["device_name"] = raw.local_name
            metadata["model"] = raw.local_name

        id_hash = hashlib.sha256(
            f"audio_technica:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="audio_technica",
            beacon_type="audio_technica",
            device_class="audio",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
