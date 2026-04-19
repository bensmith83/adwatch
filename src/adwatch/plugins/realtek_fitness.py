"""Realtek / white-label fitness-watch parser (0x0AF0 service).

A whole family of cheap Chinese BT-calling fitness watches (IDW20, BIGGERFIVE
Brave 2, Fitpolo, TOOBUR, and dozens of other re-brands of the same OEM
hardware) advertise service UUID `0x0AF0` with a manufacturer-data payload
shaped:

    [CID:2LE] [embedded_id:6] 0x02 0x01 [state:1] 0x01 0x01 0x01

Neither the CIDs (0xAB1E, 0x1F33, ...) nor the 0x0AF0 UUID are SIG-registered;
they are vendor-specific constants baked into the shared Realtek firmware
SDK. The embedded 6 bytes are MAC-shaped (typically starting with `F4`) and
appear to be a stable per-device identifier, distinct from the outer BLE MAC
which may be randomized. We prefer it for identity hashing.

See `docs/protocols/realtek-fitness-0af0.md` for observed sightings.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


RTK_FITNESS_SERVICE_UUID = "0af0"
_PIVOT = b"\x02\x01"  # observed separator between id and state bytes


@register_parser(
    name="realtek_fitness",
    service_uuid=RTK_FITNESS_SERVICE_UUID,
    description="Realtek/OEM white-label fitness watch (0x0AF0 family: IDW20, BIGGERFIVE, Fitpolo, ...)",
    version="1.0.0",
    core=False,
)
class RealtekFitnessParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        uuids = [u.lower() for u in (raw.service_uuids or [])]
        if RTK_FITNESS_SERVICE_UUID not in uuids:
            return None

        mfg = raw.manufacturer_data or b""
        metadata: dict = {}
        identity_source = raw.mac_address

        if raw.local_name:
            metadata["device_name"] = raw.local_name

        if len(mfg) >= 10:
            cid = int.from_bytes(mfg[:2], "little")
            metadata["vendor_cid"] = cid
            device_id_bytes = mfg[2:8]
            # Accept the 6-byte embedded id only if the 0x02 0x01 pivot is
            # where we expect it -- this keeps us honest against other vendors
            # that happen to use 0x0AF0.
            if mfg[8:10] == _PIVOT:
                metadata["device_id"] = ":".join(f"{b:02x}" for b in device_id_bytes)
                identity_source = device_id_bytes.hex()
                if len(mfg) >= 11:
                    metadata["state_byte"] = mfg[10]

        id_hash = hashlib.sha256(
            f"{identity_source}:realtek_fitness".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="realtek_fitness",
            beacon_type="realtek_fitness",
            device_class="fitness_watch",
            identifier_hash=id_hash,
            raw_payload_hex=mfg.hex(),
            metadata=metadata,
        )
