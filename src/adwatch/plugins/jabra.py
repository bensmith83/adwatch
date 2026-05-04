"""Jabra (GN Netcom) earbuds / headsets plugin.

Per apk-ble-hunting/reports/jabra-moments_passive.md:

  - SIG service UUID 0xFEFF (GN Netcom).
  - 8-byte mfr-data:
      [0]   attsGnServTypeBeacon  (state-flag byte)
      [1-2] product_id (uint16 LE) — 0x3010/0x3011/0x3012 known
      [3-6] unique_id (uint32 LE) — persistent per-unit identifier
      [7]   TX power (signed)
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


JABRA_SERVICE_UUID = "feff"

PRODUCT_FAMILIES = {
    0x3010: "Evolve",
    0x3011: "Engage",
    0x3012: "Talk",
}


@register_parser(
    name="jabra",
    service_uuid=JABRA_SERVICE_UUID,
    local_name_pattern=r"^Jabra ",
    description="Jabra / GN Netcom earbuds & headsets",
    version="1.0.0",
    core=False,
)
class JabraParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        uuid_hit = (
            JABRA_SERVICE_UUID in normalized
            or any(u.endswith("0000feff-0000-1000-8000-00805f9b34fb") for u in normalized)
        )
        name_hit = bool(raw.local_name and raw.local_name.startswith("Jabra "))

        if not (uuid_hit or name_hit):
            return None

        metadata: dict = {"vendor": "Jabra"}

        # 8-byte mfr-data decode (any company ID — Jabra ignores).
        payload = raw.manufacturer_payload
        unique_id = None
        if payload and len(payload) >= 8:
            metadata["serv_type_beacon"] = payload[0]
            product_id = payload[1] | (payload[2] << 8)
            metadata["product_id"] = product_id
            metadata["product_family"] = PRODUCT_FAMILIES.get(
                product_id, f"unknown_{product_id:04x}"
            )
            unique_id = (
                payload[3]
                | (payload[4] << 8)
                | (payload[5] << 16)
                | (payload[6] << 24)
            )
            metadata["unique_id"] = unique_id
            metadata["unique_id_hex"] = f"{unique_id:08x}"
            tx = payload[7]
            metadata["tx_power"] = tx - 256 if tx >= 128 else tx

        if raw.local_name:
            metadata["device_name"] = raw.local_name

        # Identity prefers the persistent 4-byte unique_id (defeats MAC rotation).
        if unique_id is not None:
            id_basis = f"jabra:{unique_id:08x}"
        else:
            id_basis = f"jabra:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        raw_hex = raw.manufacturer_data.hex() if raw.manufacturer_data else ""

        return ParseResult(
            parser_name="jabra",
            beacon_type="jabra",
            device_class="audio",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )

    def storage_schema(self):
        return None
