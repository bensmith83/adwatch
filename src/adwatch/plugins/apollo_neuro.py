"""Apollo Neuro (Apollo Neuroscience) wearable plugin.

Per apk-ble-hunting/reports/apolloneuro-apollo_passive.md.

The app discovers the wearable with exactly one advertisement signature::

    ScanFilter.Builder().setManufacturerData(1953, null)   // 0x07A1, no mask

SIG company ID **0x07A1 = "Apollo Neuroscience, Inc."** (see
``_bt_company_ids.py``), which appears in the raw bytes little-endian as
``a1 07``. No name filter, no service-UUID filter, and no code anywhere reads
the manufacturer payload bytes — the advertisement is treated purely as a
presence beacon. The payload is therefore surfaced as hex and explicitly marked
undecoded rather than given an invented layout.

The app scans with ``setLegacy(false)`` and ``setPhy(ALL_PHYS)``, so these are
BLE 5.0 **extended** advertisements — a scanner needs extended-advertising
support to see them at all. That is recorded in the metadata as a capture hint.

All state (battery, firmware, vibration session) is a connected-mode protobuf
Envelope over GATT service ``00001623-1212-EFDE-1523-785FEABCD124``.

Privacy: a fixed company ID broadcast continuously permits passive presence
tracking of an Apollo wearer — a health-adjacent (stress/recovery therapy)
inference. Flagged ``sensitive=True``.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


# SIG company ID for "Apollo Neuroscience, Inc." — 1953 decimal.
APOLLO_COMPANY_ID = 0x07A1


@register_parser(
    name="apollo_neuro",
    company_id=APOLLO_COMPANY_ID,
    description="Apollo Neuro wearable (presence beacon, CID 0x07A1)",
    version="1.0.0",
    core=False,
)
class ApolloNeuroParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if raw.company_id != APOLLO_COMPANY_ID:
            return None

        payload = raw.manufacturer_payload or b""
        metadata: dict = {
            "vendor": "Apollo Neuroscience",
            "product": "Apollo Neuro",
            "company_id": APOLLO_COMPANY_ID,
            "mfr_payload_hex": payload.hex(),
            "mfr_payload_len": len(payload),
            # The app filters on the company ID with a null mask and never
            # reads the bytes, so no layout is asserted.
            "mfr_payload_decoded": False,
            "extended_advertising": True,
            "telemetry": "none (connect-only GATT)",
            "sensitive": True,
            "sensitive_category": "stress_therapy",
        }
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        # No verified per-unit identifier exists in the payload, so the MAC is
        # the only anchor available.
        id_hash = hashlib.sha256(
            f"apollo_neuro:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="apollo_neuro",
            beacon_type="apollo_neuro",
            device_class="wearable",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
