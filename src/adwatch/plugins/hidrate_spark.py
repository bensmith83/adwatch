"""HidrateSpark smart water bottle plugin.

Per apk-ble-hunting/reports/hidratenow-hidrate_passive.md the bottle's
entire passive surface is its advertised name:

    h2o<serialNumber>

The app scans with an empty ``ScanFilter`` and accepts a result iff the
lower-cased name contains ``"h2o"``
(`RxBLEBottleConnectionManager.java:2551`, `:1331`), then derives the
serial with ``name.replace("h2o", "")`` (`:2521`) and confirms it against
the GATT Serial Number characteristic (`:2920`).

There is **no** manufacturer data, **no** service data and **no** broadcast
telemetry -- fill level, sips, battery and water total are all GATT-only.
So the privacy story is identity, not activity: the serial is a stable,
non-rotating identifier broadcast in the clear, which makes the bottle (and
its owner) trivially trackable. That serial is therefore the identity-hash
basis, and it stays stable even if the BLE MAC rotates.

Matching is anchored to the documented ``h2o`` *prefix* with at least two
serial characters rather than the app's looser substring test, so that
unrelated devices with "h2o" somewhere in their name are not claimed.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


HIDRATE_NAME_PATTERN = r"(?i)^h2o[0-9A-Za-z]{2,}$"

_NAME_RE = re.compile(HIDRATE_NAME_PATTERN)
_PREFIX_RE = re.compile(r"(?i)^h2o")


def extract_serial(local_name: str | None) -> str | None:
    """Return the serial tail of an ``h2o<serial>`` name, else None."""
    if not local_name or not _NAME_RE.match(local_name):
        return None
    return _PREFIX_RE.sub("", local_name, count=1)


@register_parser(
    name="hidrate_spark",
    local_name_pattern=HIDRATE_NAME_PATTERN,
    description="HidrateSpark smart water bottle",
    version="1.0.0",
    core=False,
)
class HidrateSparkParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        serial = extract_serial(raw.local_name)
        if serial is None:
            return None

        metadata: dict = {
            "vendor": "Hidrate",
            "model": "HidrateSpark",
            "device_name": raw.local_name,
            "serial_number": serial,
            # Non-rotating serial in the clear: presence/identity is
            # trackable even though no behaviour leaks passively.
            "persistent_identifier": True,
            "passive_telemetry": False,
        }

        id_basis = f"hidrate_spark:{serial}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="hidrate_spark",
            beacon_type="hidrate_spark",
            device_class="bottle",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
            stable_key=id_basis,
        )

    def storage_schema(self):
        return None
