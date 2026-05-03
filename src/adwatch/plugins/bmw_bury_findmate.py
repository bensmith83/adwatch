"""BMW Find Mate (Bury Technologies BLE tracker tag) plugin.

Per apk-ble-hunting/reports/bmw-connected_passive.md:

  - The only BLE surface in the BMW Connected app is the Bury-supplied
    "BMW Find Mate" luggage / key tracker tag. The vehicle itself uses
    Classic BT (BMW NA, 2020-era) — invisible to a BLE scanner.

  - The tag advertises with one of two exact device names:
      "BMW FMT" — factory / unregistered state ("Find Mate Tag" default)
      "BMW FM1" — registered to a phone ("Find Mate #1")

  No mfr-data, no service-data parsed by the app. Discovery is by Complete
  Local Name AD field only.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


_NAMES = ("BMW FMT", "BMW FM1")


@register_parser(
    name="bmw_bury_findmate",
    local_name_pattern=r"^BMW (FMT|FM1)$",
    description="BMW Find Mate (Bury BLE tracker tag) — BMW-branded white-label",
    version="1.0.0",
    core=False,
)
class BmwBuryFindMateParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if raw.local_name not in _NAMES:
            return None

        metadata: dict = {
            "vendor": "Bury Technologies",
            "brand": "BMW",
            "product": "Find Mate Tag",
        }
        if raw.local_name == "BMW FMT":
            metadata["state"] = "unregistered"
            metadata["state_label"] = "factory_fresh"
        else:  # BMW FM1
            metadata["state"] = "registered"
            metadata["state_label"] = "previously_paired"

        id_hash = hashlib.sha256(
            f"bmw_bury_findmate:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="bmw_bury_findmate",
            beacon_type="bmw_bury_findmate",
            device_class="tracker",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
