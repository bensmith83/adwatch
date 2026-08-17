"""Ledger hardware-wallet plugin (Nano X / Flex / Stax / Apex).

Per apk-ble-hunting/reports/ledger-live_passive.md (com.ledger.live).

Ledger devices advertise a product-family 128-bit service UUID of the form::

    13d63400-2c97-XXXX-NNNN-4c6564676572
    ^^^^^^^^^^^^^^                ^^^^^^^^^^^^
    fixed prefix                  ASCII "Ledger"

with the family word ``XXXX`` selecting the product (Nano X ``0004``, Flex
``3004``, Stax/Apex ``6004``; ``8004``/``9004`` appear in the Hermes bundle for
unreleased families). The tail bytes ``4c 65 64 67 65 72`` spell ``Ledger`` —
one of the cleanest vendor signatures in BLE UUID space.

The advertisement carries **identity only**: the product name is broadcast
verbatim (``Nano X``, ``Ledger Stax``, ``Ledger Flex``, ``Ledger Apex``) and
there is no manufacturer data, no service data and no per-unit serial. All
units of a product family look identical apart from the BLE MAC, which is
therefore the identity basis.

Note the privacy angle called out in the report: a Ledger advertisement
discloses "this person carries a hardware crypto wallet".
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


NANO_X_UUID = "13d63400-2c97-0004-0000-4c6564676572"
FLEX_UUID = "13d63400-2c97-3004-0000-4c6564676572"
STAX_UUID = "13d63400-2c97-6004-0000-4c6564676572"
# Surfaced in the Hermes bundle but mapped to no shipping product.
SPECULATIVE_8004_UUID = "13d63400-2c97-8004-0000-4c6564676572"
SPECULATIVE_9004_UUID = "13d63400-2c97-9004-0000-4c6564676572"

LEDGER_SERVICE_UUIDS = [
    NANO_X_UUID,
    FLEX_UUID,
    STAX_UUID,
    SPECULATIVE_8004_UUID,
    SPECULATIVE_9004_UUID,
]

LEDGER_NAME_RE = r"^(Nano X|Ledger (Nano X|Stax|Flex|Apex))\b"

# `13d63400-2c97-<family>-<role>-4c6564676572`; role 0000 is the service,
# 0001-0003 are the notify/write characteristics.
_LEDGER_UUID_RE = re.compile(
    r"^13d63400-2c97-([0-9a-f]{4})-([0-9a-f]{4})-4c6564676572$"
)

FAMILY_MODELS = {
    "0004": "Ledger Nano X",
    "3004": "Ledger Flex",
    # Apex is backwards-compatible with the Stax BLE stack and shares its UUID.
    "6004": "Ledger Stax / Apex",
}

NAME_MODELS = {
    "nano x": "Ledger Nano X",
    "ledger nano x": "Ledger Nano X",
    "ledger flex": "Ledger Flex",
    "ledger stax": "Ledger Stax",
    "ledger apex": "Ledger Apex",
}


@register_parser(
    name="ledger_wallet",
    service_uuid=LEDGER_SERVICE_UUIDS,
    local_name_pattern=LEDGER_NAME_RE,
    description="Ledger hardware wallets (Nano X / Flex / Stax / Apex)",
    version="1.0.0",
    core=False,
)
class LedgerWalletParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        matched_uuid = None
        family = None
        for u in (raw.service_uuids or []):
            m = _LEDGER_UUID_RE.match(u.lower())
            if m:
                matched_uuid = u.lower()
                family = m.group(1)
                break

        name = (raw.local_name or "").strip()
        name_model = NAME_MODELS.get(name.lower())

        if matched_uuid is None and name_model is None:
            return None

        metadata: dict = {
            "vendor": "Ledger",
            "uuid_vendor_signature": "Ledger",
            "service_uuid_match": matched_uuid is not None,
        }

        if matched_uuid is not None:
            metadata["service_uuid"] = matched_uuid
            metadata["family_code"] = family

        # A broadcast name pins Stax vs Apex, which share one service UUID.
        if name_model is not None:
            metadata["model"] = name_model
        elif family is not None:
            metadata["model"] = FAMILY_MODELS.get(
                family, f"Ledger (unknown family {family})"
            )

        if name:
            metadata["device_name"] = name

        return ParseResult(
            parser_name="ledger_wallet",
            beacon_type="ledger_wallet",
            device_class="hardware_wallet",
            identifier_hash=hashlib.sha256(
                f"ledger:{raw.mac_address}".encode()
            ).hexdigest()[:16],
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
