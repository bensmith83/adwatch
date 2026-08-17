"""Medtronic / Companion InPen smart insulin pen plugin.

Per apk-ble-hunting/reports/companionmedical-inpen_passive.md:

  - The app's only scan filter is the 16-bit service UUID ``0xBFD0``
    (``0000BFD0-0000-1000-8000-00805F9B34FB``). No name filter, no company ID.
  - ``AdvertisementData`` (``penble_mediator_service/a.java:40-43``) reads
    *absolute* scan-record offsets, without AD-type validation:

      offset 10      -> ``m_alertFlags`` status/alert byte
      offsets 11..13 -> 3-byte pen ID, little-endian on air, rendered
                        big-endian as ``%02x%02x%02x`` of record[13,12,11]

    For a record that starts with the Flags AD, a 3-byte AD and then the
    element carrying this data, offsets 10..13 fall inside that element's
    *value* (a manufacturer-data element's value starts right after the 2-byte
    company ID; a 16-bit service-data element's value starts right after the
    2-byte UUID). So value[0] is the alert byte and value[1:4] is the pen ID.
    The app itself never validates the framing, so treat both offsets as
    "as documented, verify against a live capture" — hence the payload is
    optional and matching never depends on it.

  - Dose data is *not* broadcast; it requires the AES-bonded GATT session.
    The 3-byte pen ID is a stable cleartext identifier, so it (not the MAC)
    is the identity-hash basis.
"""

import hashlib

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import register_parser


INPEN_SERVICE_UUID = "bfd0"
INPEN_SERVICE_UUID_FULL = "0000bfd0-0000-1000-8000-00805f9b34fb"

# AdvertisementData.d(): the app treats a pen as "in range" above -95 dBm.
INPEN_IN_RANGE_RSSI = -95


@register_parser(
    name="medtronic_inpen",
    service_uuid=(INPEN_SERVICE_UUID, INPEN_SERVICE_UUID_FULL),
    description="Medtronic/Companion InPen smart insulin pen",
    version="1.0.0",
    core=False,
)
class MedtronicInPenParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        advertised = [u.lower() for u in (raw.service_uuids or [])]
        svc_data = raw.service_data or {}
        uuid_hit = (
            INPEN_SERVICE_UUID in advertised
            or INPEN_SERVICE_UUID_FULL in advertised
            or INPEN_SERVICE_UUID in svc_data
            or INPEN_SERVICE_UUID_FULL in svc_data
        )
        if not uuid_hit:
            return None

        metadata: dict = {"product": "Medtronic InPen smart insulin pen"}
        if raw.local_name:
            metadata["device_name"] = raw.local_name
        metadata["in_range"] = raw.rssi > INPEN_IN_RANGE_RSSI

        value = svc_data.get(INPEN_SERVICE_UUID) or svc_data.get(INPEN_SERVICE_UUID_FULL)
        source = "service_data"
        if not value:
            value = raw.manufacturer_payload
            source = "manufacturer_data"

        pen_id = None
        if value and len(value) >= 4:
            metadata["alert_flags"] = value[0]
            metadata["alert_flags_hex"] = f"{value[0]:02x}"
            pen_id = f"{value[3]:02x}{value[2]:02x}{value[1]:02x}"
        elif value and len(value) == 3:
            # No leading flag byte in this framing; the whole value is the ID.
            pen_id = f"{value[2]:02x}{value[1]:02x}{value[0]:02x}"

        if pen_id is not None:
            metadata["pen_id"] = pen_id
            metadata["payload_source"] = source

        id_basis = f"inpen:{pen_id}" if pen_id else f"inpen:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        raw_hex = value.hex() if value else ""

        return ParseResult(
            parser_name="medtronic_inpen",
            beacon_type="medtronic_inpen",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )

    def storage_schema(self):
        return None
