"""Alibaba AIS plugin (covers ECOVACS DEEBOT/WINBOT + AliGenie OEMs).

Per apk-ble-hunting/reports/eco-global-app_passive.md. Alibaba's IoT
cloud onboards diverse OEMs with a unified BLE advertisement format
under SIG CID ``0x01A8`` (Alibaba Group, 424). The post-CID payload:

  - [0]    subtype (high nibble) + version (low nibble):
            * ``0x08`` basic — full PID + BD_ADDR
            * ``0x09`` beacon — compact (PID low 2B + BD_ADDR)
            * ``0x0A`` gma
  - [1]    feature mask byte (FMask)
  - **basic / gma**:
      - [2..5] PID (uint32 big-endian — bytes [5][4][3][2] in payload)
      - [6..11] BD_ADDR (bytes reversed from on-wire LE)
  - **beacon**:
      - [2..3] PID (low 2 bytes only, padded high)
      - [4..9] BD_ADDR (reversed)

The advertised BD_ADDR is the device's TRUE Bluetooth MAC even when the
BLE-layer address has been randomized — used here as a stable identity-
hash basis. Plus name regex covering ``DEEBOT-…`` / ``WINBOT-…`` /
``ECOVACS_…`` / ``ALI-…``.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


ALIBABA_CID = 0x01A8  # 424

_NAME_RE = re.compile(r"^(DEEBOT|WINBOT|ECOVACS|ALI-)")

_SUBTYPE_NAMES = {
    0x08: "basic",
    0x09: "beacon",
    0x0A: "gma",
}


@register_parser(
    name="alibaba_ais",
    company_id=ALIBABA_CID,
    local_name_pattern=r"^(DEEBOT|WINBOT|ECOVACS|ALI-)",
    description="Alibaba AIS (ECOVACS DEEBOT/WINBOT + AliGenie OEMs)",
    version="1.0.0",
    core=False,
)
class AlibabaAisParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        cid_hit = raw.company_id == ALIBABA_CID
        local_name = raw.local_name or ""
        name_match = _NAME_RE.match(local_name)

        if not (cid_hit or name_match):
            return None

        # iRobot's mfr-data also uses CID 0x01A8 — gate the AIS decode on
        # the AIS subtype byte in the high nibble of payload[0].
        metadata: dict = {"vendor": "Alibaba"}
        if local_name:
            metadata["device_name"] = local_name

        embedded_mac: str | None = None
        if cid_hit:
            payload = raw.manufacturer_payload or b""
            if len(payload) >= 1:
                first = payload[0]
                subtype = (first >> 4) & 0x0F
                version = first & 0x0F
                subtype_name = _SUBTYPE_NAMES.get(subtype)
                if subtype_name is None:
                    # Not an AIS frame — leave to other CID-0x01A8 parsers
                    # (e.g. iRobot, Mammotion). Only claim a sighting if a
                    # name match also fired.
                    if not name_match:
                        return None
                else:
                    metadata["ais_subtype"] = subtype_name
                    metadata["ais_version"] = version
                    if len(payload) >= 2:
                        metadata["fmask"] = payload[1]

                    if subtype in (0x08, 0x0A) and len(payload) >= 12:
                        # PID big-endian at offset 2..5.
                        metadata["product_id"] = int.from_bytes(payload[2:6], "big")
                        # BD_ADDR reversed at offset 6..11.
                        mac_bytes = bytes(reversed(payload[6:12]))
                        embedded_mac = ":".join(f"{b:02X}" for b in mac_bytes)
                        metadata["embedded_mac"] = embedded_mac
                    elif subtype == 0x09 and len(payload) >= 10:
                        # Beacon: PID low 2 bytes (LE) at offset 2..3.
                        metadata["product_id"] = int.from_bytes(payload[2:4], "little")
                        mac_bytes = bytes(reversed(payload[4:10]))
                        embedded_mac = ":".join(f"{b:02X}" for b in mac_bytes)
                        metadata["embedded_mac"] = embedded_mac

        if embedded_mac:
            id_basis = f"alibaba_ais:{embedded_mac}"
        else:
            id_basis = f"alibaba_ais:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="alibaba_ais",
            beacon_type="alibaba_ais",
            device_class="smart_home",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
