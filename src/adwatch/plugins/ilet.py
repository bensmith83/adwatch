"""Beta Bionics iLet bionic pancreas (automated insulin delivery) parser.

The iLet is an FDA-cleared (K231485, May 2023) AID pump from Beta Bionics.
Observed BLE advertisement:
  - local_name: ``iLet4-<4hex>`` (the suffix appears stable per pump)
  - service_uuids: ``A0090101-0605-0403-0201-F0E0D0C0B0A0``

The 128-bit UUID looks like an engineer-picked placeholder rather than a
randomly generated one (trailing bytes are a descending count: 06-05-04-03-02-01
then F0-E0-D0-C0-B0-A0). Whether placeholder or not, it is the UUID shipped
on real iLet hardware in the wild.

See ``docs/protocols/beta-bionics-ilet.md`` for references.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser, _normalize_uuid


ILET_SERVICE_UUID = "a0090101-0605-0403-0201-f0e0d0c0b0a0"
_ILET_SERVICE_UUID_NORM = _normalize_uuid(ILET_SERVICE_UUID)
_NAME_RE = re.compile(r"^(iLet\d+)-([0-9A-Fa-f]{4})$")


@register_parser(
    name="ilet",
    service_uuid=ILET_SERVICE_UUID,
    local_name_pattern=r"^iLet\d+-[0-9A-Fa-f]{4}",
    description="Beta Bionics iLet bionic pancreas (automated insulin delivery)",
    version="1.0.0",
    core=False,
)
class ILetParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        name = raw.local_name or ""
        uuids = {_normalize_uuid(u) for u in (raw.service_uuids or [])}

        name_match = _NAME_RE.match(name)
        has_uuid = _ILET_SERVICE_UUID_NORM in uuids

        if not name_match and not has_uuid:
            return None

        metadata: dict = {}
        identity_source = raw.mac_address
        if name:
            metadata["device_name"] = name
        if name_match:
            metadata["hardware_rev"] = name_match.group(1)
            metadata["device_suffix"] = name_match.group(2).upper()
            identity_source = metadata["device_suffix"]

        id_hash = hashlib.sha256(
            f"{identity_source}:ilet".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="ilet",
            beacon_type="ilet",
            device_class="medical_device",
            identifier_hash=id_hash,
            raw_payload_hex=raw.manufacturer_data.hex() if raw.manufacturer_data else "",
            metadata=metadata,
        )
