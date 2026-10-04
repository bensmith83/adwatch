"""Sensate (BioSelf) vagus-nerve relaxation puck presence plugin.

Per apk-ble-hunting/reports/bioself-sensatepebble_passive.md.

The vendor app uses legacy ``startLeScan`` with no filter and matches only on
the advertised name containing ``Sensate`` / ``BioSelf`` / ``ARC BOOT``
(``ARC BOOT`` = DFU/bootloader mode). The scan record is ignored, so there is
no mfr/service-data layout to decode. Matching is relaxed to case-insensitive
per the report (also covers the ``besensate10`` factory-name hint).

Identity = MAC (no in-advert id).
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


SENSATE_NAME_PATTERN = r"(?i)(sensate|bioself|arc boot)"
_NAME_RE = re.compile(SENSATE_NAME_PATTERN)
_DFU_RE = re.compile(r"(?i)arc boot")


@register_parser(
    name="sensate",
    local_name_pattern=SENSATE_NAME_PATTERN,
    description="Sensate (BioSelf) relaxation puck (presence-only, name substring)",
    version="1.0.0",
    core=False,
)
class SensateParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        name = raw.local_name or ""
        if not _NAME_RE.search(name):
            return None

        metadata: dict = {
            "vendor": "BioSelf",
            "product": "Sensate",
            "device_name": name,
            "dfu_mode": bool(_DFU_RE.search(name)),
            "telemetry": "none (GATT only)",
        }
        mfr = raw.manufacturer_data
        if mfr:
            metadata["mfr_data_hex"] = mfr.hex()

        id_hash = hashlib.sha256(f"sensate:{raw.mac_address}".encode()).hexdigest()[:16]
        return ParseResult(
            parser_name="sensate",
            beacon_type="sensate",
            device_class="wearable",
            identifier_hash=id_hash,
            raw_payload_hex=(mfr or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
