"""Zengge / Magic Light LED bulb plugin.

Per apk-ble-hunting/reports/zengge-magiclight_passive.md. Zengge bulbs
use the commodity HM-10 module (service UUID ``0xFFE0``) and identify
via 7 OEM name prefixes:

  - ``LEDBlue`` / ``LEDBLE`` / ``LEDSpeaker`` / ``LEDShoe`` / ``LEDnet``
  - ``FluxBlue`` (FluxSmart-branded)
  - ``TIBURN`` (TIBURN reseller)

UUID alone (``0xFFE0`` HM-10) is a vendor-agnostic commodity choice and
would false-positive on countless HM-10 products. We require the name
prefix to fire — so the registry may match by UUID but ``parse()``
returns None unless we also see one of the brand prefixes.

Per the report, the bulb's lighting state is post-connect-only; the
broadcast is presence + product-class fingerprint only.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


ZENGGE_HM10_UUID = "ffe0"
_HM10_FULL = "0000ffe0-0000-1000-8000-00805f9b34fb"

_BRAND_RE = re.compile(
    r"^(LEDBlue|LEDBLE|LEDSpeaker|LEDShoe|LEDnet|FluxBlue|TIBURN)"
)


@register_parser(
    name="zengge",
    service_uuid=ZENGGE_HM10_UUID,
    local_name_pattern=r"^(LEDBlue|LEDBLE|LEDSpeaker|LEDShoe|LEDnet|FluxBlue|TIBURN)",
    description="Zengge / Magic Light LED bulbs (HM-10 + 7-prefix name catalog)",
    version="1.0.0",
    core=False,
)
class ZenggeParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        local_name = raw.local_name or ""
        name_match = _BRAND_RE.match(local_name)
        if not name_match:
            return None

        metadata: dict = {
            "vendor": "Zengge",
            "brand": name_match.group(1),
            "device_name": local_name,
        }

        normalized = [u.lower() for u in (raw.service_uuids or [])]
        if ZENGGE_HM10_UUID in normalized or _HM10_FULL in normalized:
            metadata["hm10_service_seen"] = True

        id_basis = f"zengge:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="zengge",
            beacon_type="zengge",
            device_class="smart_light",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
