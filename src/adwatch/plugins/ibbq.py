"""iBBQ / EasyBBQ / BBQ Go / GrillEye BBQ thermometer plugin.

Byte layout per apk-ble-hunting reports `easybbq_passive.md` (pkg
`qlnet.com.easybbq`) and `bbqgo_passive.md` (pkg `qlnet.com.bbqgo`), which
independently decompiled the same protocol from two OEM apps.

Both apps use the legacy `startLeScan` API with no ScanFilter: they walk the
raw AD structures looking for AD type 0xFF and decode from the *length* byte
of that structure (``S``):

    S+0        AD length L            probe count = (L - 11) / 2
    S+1        AD type 0xFF
    S+2        sub-opcode             0x01 temps, 0x02 channel run-time,
                                      0x11/0x12 device-type-1 markers
    S+3, S+4   header bytes           opaque
    S+5        flag byte              0x80 = QTECH hardware variant,
                                      0x08 = confirm-package / pairing ready
    S+6..S+11  device MAC             persistent, survives BLE MAC rotation
    S+12..     2*N probe fields       int16 LE / 10 = degC (or u16 * 3 = s)

``RawAdvertisement.manufacturer_data`` begins at S+2, so the in-payload
header is 10 bytes (the framework's "company ID" is really sub-opcode +
header byte -- these devices do not use a real SIG company ID). Matching is
therefore on the model name only; the reports confirm the app filters the
same way.
"""

import hashlib
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


# manufacturer_data[0:10] = subop(1) + header(2) + flag(1) + mac(6)
IBBQ_HEADER_LEN = 10
IBBQ_MAC_OFFSET = 4

IBBQ_NAME_PATTERN = r"^(iBBQ|xBBQ|GrillEye)"

SUBOP_TEMPERATURES = 0x01
SUBOP_CHANNEL_RUNTIME = 0x02
SUBOP_DEVICE_TYPE_1 = 0x11
SUBOP_DEVICE_TYPE_1_ALT = 0x12

SUBOP_NAMES = {
    SUBOP_TEMPERATURES: "temperatures",
    SUBOP_CHANNEL_RUNTIME: "channel_runtime",
    SUBOP_DEVICE_TYPE_1: "device_type_marker",
    SUBOP_DEVICE_TYPE_1_ALT: "device_type_marker",
}

FLAG_QTECH_VARIANT = 0x80
FLAG_CONFIRM_PACKAGE = 0x08

# Probe-absent sentinels. The bbqpro path divides by 10 and compares against
# -1.0f (raw -10 / 0xFFF6); the report tables also cite 0xFFFF. Both are
# implausible as real readings, so both are treated as "no probe".
TEMP_ABSENT_RAW = (-1, -10)
RUNTIME_NOT_RUNNING = 0xFFFF
RUNTIME_UNIT_SECONDS = 3  # raw u16 * 3 = seconds


def _format_mac(mac_bytes: bytes) -> str:
    return ":".join(f"{b:02x}" for b in mac_bytes)


@register_parser(
    name="ibbq",
    local_name_pattern=IBBQ_NAME_PATTERN,
    description="iBBQ / EasyBBQ / BBQ Go / GrillEye BBQ thermometer",
    version="2.0.0",
    core=False,
)
class IBBQParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        payload = raw.manufacturer_data
        if not payload or len(payload) < IBBQ_HEADER_LEN:
            return None

        sub_op = payload[0]
        flag = payload[3]
        mac_bytes = payload[IBBQ_MAC_OFFSET:IBBQ_HEADER_LEN]
        fields = payload[IBBQ_HEADER_LEN:]
        field_count = len(fields) // 2

        metadata: dict = {
            "sub_op": sub_op,
            "sub_op_name": SUBOP_NAMES.get(sub_op, "temperatures"),
        }
        if raw.local_name:
            metadata["model"] = raw.local_name
        if flag == FLAG_QTECH_VARIANT:
            metadata["qtech_variant"] = True
        elif flag == FLAG_CONFIRM_PACKAGE:
            metadata["confirm_package"] = True

        # Persistent in-payload MAC (survives BLE MAC randomisation).
        embedded_mac = None
        if any(mac_bytes) and mac_bytes != b"\xff" * 6:
            embedded_mac = _format_mac(mac_bytes)
            metadata["device_mac"] = embedded_mac

        if sub_op in (SUBOP_DEVICE_TYPE_1, SUBOP_DEVICE_TYPE_1_ALT):
            # Marker frames carry no passive telemetry body.
            metadata["device_type"] = 1
        elif sub_op == SUBOP_CHANNEL_RUNTIME:
            if field_count == 0:
                return None
            metadata["probe_count"] = field_count
            for i in range(field_count):
                value = struct.unpack_from("<H", fields, i * 2)[0]
                if value == RUNTIME_NOT_RUNNING:
                    continue
                metadata[f"probe_{i + 1}_runtime_s"] = value * RUNTIME_UNIT_SECONDS
        else:
            # 0x01 and the legacy path (which ignores the byte entirely).
            if field_count == 0:
                return None
            metadata["probe_count"] = field_count
            for i in range(field_count):
                value = struct.unpack_from("<h", fields, i * 2)[0]
                if value in TEMP_ABSENT_RAW:
                    continue
                metadata[f"probe_{i + 1}_temp_c"] = value / 10.0

        if embedded_mac is not None:
            id_basis = f"ibbq:{embedded_mac}"
        else:
            id_basis = f"ibbq:mac:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="ibbq",
            beacon_type="ibbq",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
