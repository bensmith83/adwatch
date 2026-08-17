"""Nordlux Smart Light / Yankon proprietary mesh beacon plugin.

Per apk-ble-hunting/reports/nordlux-smartlight_passive.md
(`DeviceDescriptionUtil.java:56-324`,
`BluetoothLeScanManager.java:175-300`). Nordlux bulbs advertise in three
shapes; the SIG Mesh Provisioning (`0x1827`) and Mesh Proxy (`0x1828`)
beacons are vendor-agnostic and already handled by ``plugins/bt_mesh.py``,
so only the Yankon/NX proprietary manufacturer-data beacon is decoded here.

Company ID ``0x6E78`` (on air: ``78 6E``), payload exactly 24 bytes. The
report's offsets are already relative to the payload after the company ID,
so they map straight onto ``manufacturer_payload``:

    [0:4]   beacon type / model code, ASCII, byte-reversed
    [4]     unknown
    [5]     chip type
    [6]     firmware major
    [7:9]   specNetKey index   (0x0000 => not provisioned)
    [9:11]  specAppKey index   (0x0000 => not provisioned)
    [11:17] device ID, 6 bytes reversed -- MAC-derived, persistent
    [17:19] mesh unicast address
    [19]    firmware minor
    [20]    UV (room) group
    [22]    room id
    [23]    checksum = sum(payload[0:23]) & 0xFF

The checksum is the app's own ``checkDeviceIsYankon()`` gate and doubles as
a strong false-positive guard on this company ID, so a payload that fails
it is rejected.

Byte-order caveat: the decompile reverses each multi-byte integer field
before parsing it as hex, which is a little-endian read of the original
bytes -- that is what is implemented. The report's phrasing ("uint16 LE,
then byte-flipped") is self-contradictory, so the raw bytes of each of
those fields are also exposed as ``*_hex`` for re-derivation if a live
capture ever disagrees.

Identity is the 6-byte device ID: persistent across provisioning cycles and
independent of the BLE MAC.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


YANKON_COMPANY_ID = 0x6E78
YANKON_PAYLOAD_LEN = 24

MESH_PROV_UUID = "00001827-0000-1000-8000-00805f9b34fb"
MESH_PROXY_UUID = "00001828-0000-1000-8000-00805f9b34fb"

# BleDeviceTypeByBeacon.java:4-93 (partial table from the report).
MODEL_CODES = {
    "nx0002": "A60 bulb",
    "nx0004": "GU10 bulb",
    "nx0008": "Gateway",
    "nx0011": "A60 filament",
    "nx0012": "A60 filament",
    "nx0018": "E14 candle",
    "nx0019": "E14 globe",
    "nx0020": "E27 colour",
    "nx0021": "GU10 colour",
    "nx0022": "GU10 glass",
    "nx0023": "E27 clear",
    "nx0047": "Smart plug",
}


def checksum(body: bytes) -> int:
    """Low byte of the sum of payload bytes 0..22."""
    return sum(body) & 0xFF


def lookup_model(beacon_type: str) -> str | None:
    """Map a beacon-type code to a product label.

    The decompile returns only the first 4 characters of the reversed
    ASCII, while the model table is keyed on the 6-character ``nx00NN``
    form, so a bare 4-digit code is retried with the ``nx`` prefix.
    """
    key = beacon_type.lower()
    if key in MODEL_CODES:
        return MODEL_CODES[key]
    if len(key) == 4 and key.isdigit():
        return MODEL_CODES.get(f"nx{key}")
    return None


def _le16(chunk: bytes) -> int:
    return int.from_bytes(chunk, "little")


@register_parser(
    name="nordlux_yankon",
    company_id=YANKON_COMPANY_ID,
    description="Nordlux Smart Light / Yankon proprietary mesh beacon",
    version="1.0.0",
    core=False,
)
class NordluxYankonParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        payload = raw.manufacturer_payload
        if not payload or len(payload) < YANKON_PAYLOAD_LEN:
            return None

        payload = payload[:YANKON_PAYLOAD_LEN]
        if payload[23] != checksum(payload[:23]):
            return None

        beacon_type = payload[0:4][::-1].decode("ascii", errors="replace")
        net_key = _le16(payload[7:9])
        app_key = _le16(payload[9:11])
        device_id = payload[11:17][::-1].hex()

        metadata: dict = {
            "vendor": "Nordlux/Yankon",
            "beacon_type": beacon_type,
            "chip_type": payload[5],
            "firmware_major": payload[6],
            "firmware_minor": payload[19],
            "spec_net_key_index": net_key,
            "spec_net_key_hex": payload[7:9].hex(),
            "spec_app_key_index": app_key,
            "spec_app_key_hex": payload[9:11].hex(),
            "provisioned": bool(net_key and app_key),
            "device_id": device_id,
            "mesh_unicast_address": _le16(payload[17:19]),
            "mesh_unicast_hex": payload[17:19].hex(),
            "uv_group": payload[20],
            "room": payload[22],
            "checksum_valid": True,
        }

        model = lookup_model(beacon_type)
        if model:
            metadata["model"] = model

        advertised = {u.lower() for u in (raw.service_uuids or [])}
        advertised.update(k.lower() for k in (raw.service_data or {}))
        if MESH_PROV_UUID in advertised:
            metadata["mesh_provisioning_beacon"] = True
        if MESH_PROXY_UUID in advertised:
            metadata["mesh_proxy_beacon"] = True

        id_basis = f"nordlux_yankon:{device_id}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="nordlux_yankon",
            beacon_type="nordlux_yankon",
            device_class="smart_light",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata=metadata,
            stable_key=id_basis,
        )

    def storage_schema(self):
        return None
