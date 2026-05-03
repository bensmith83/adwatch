"""August/Yale smart lock plugin.

Passive advertisement decode driven by
`apk-ble-hunting/reports/august-luna_passive.md` and
`reports/assaabloy-yale_passive.md`. Exposes the persistent 16-byte LockID,
lock generation (V1..V4), and keypad serial as metadata.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import _normalize_uuid, register_parser


# Company IDs the Yale/August SDK checks in priority order when extracting
# the LockID from manufacturer data. 0x004C (Apple/HomeKit mode) is omitted
# intentionally — registering it here would fire this parser on every Apple
# continuity advertisement.
_COMPANY_IDS_HEADER = {0x0016, 0x012E}        # 2-byte header + 16-byte LockID
_COMPANY_ID_TAIL_ALIGNED = 0x01D1             # tail-aligned LockID (last 16 bytes)

# Service UUIDs map to lock generation (see passive report).
_GENERATION_BY_UUID = {
    _normalize_uuid("bd4ac610-0b45-11e3-8ffd-0800200c9a66"): "V1_2014",
    _normalize_uuid("e295c550-69d0-11e4-b116-123b93f75cba"): "V2_2014",
    _normalize_uuid("fe24"): "V3_2017",
    _normalize_uuid("fcbf"): "V4_2023",
}

_KEYPAD_NAME_RE = re.compile(r"^(?:Keypad|August|ASSA ABLOY) (K\d[a-zA-Z0-9]{8})$")


@register_parser(
    name="august_yale",
    company_id=[0x0016, 0x01D1, 0x012E, 0x0BDE],
    service_uuid=[
        "fe24",
        "fcbf",
        "bd4ac610-0b45-11e3-8ffd-0800200c9a66",
        "e295c550-69d0-11e4-b116-123b93f75cba",
        "52e4c6be-0f96-425c-8900-ddcef680f636",
        "a86abc2d-d44c-442e-99f7-80059a873e36",
    ],
    local_name_pattern=_KEYPAD_NAME_RE.pattern,
    description="August/Yale smart locks and keypads",
    version="1.1.0",
    core=False,
)
class AugustYaleParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        metadata: dict = {}

        payload = raw.manufacturer_payload
        company = raw.company_id
        if payload:
            metadata["state_toggle"] = payload[0]

        lock_id = self._extract_lock_id(company, payload)
        if lock_id:
            metadata["lock_id"] = lock_id

        # Yale Connect (LatAm) 3-byte mfr-data: [version, joined, encrypted].
        # Only decode when CID is 0x012E AND we did NOT find a LockID
        # (different product family, mutually-exclusive payload shape).
        if (company == 0x012E and not lock_id and payload
                and len(payload) >= 3
                and payload[1] in (0, 1) and payload[2] in (0, 1)):
            v = payload[0]
            metadata["yale_connect"] = True
            metadata["ble_protocol_version"] = f"{(v >> 4) & 0x0F}.{v & 0x0F}"
            metadata["joined"] = bool(payload[1])
            metadata["encrypted"] = bool(payload[2])

        generation = self._detect_generation(raw)
        if generation:
            metadata["generation"] = generation

        local_name = raw.local_name or ""
        keypad_serial = None
        m = _KEYPAD_NAME_RE.match(local_name)
        if m:
            keypad_serial = m.group(1)
            metadata["device_kind"] = "keypad"
            metadata["keypad_serial"] = keypad_serial

        device_class = "keypad" if keypad_serial else "lock"

        if lock_id:
            id_basis = f"august_yale:lockid:{lock_id}"
        elif keypad_serial:
            id_basis = f"august_yale:keypad:{keypad_serial}"
        else:
            id_basis = f"{raw.mac_address}:{local_name}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        raw_hex = payload.hex() if payload else ""

        return ParseResult(
            parser_name="august_yale",
            beacon_type="august_yale",
            device_class=device_class,
            identifier_hash=id_hash,
            raw_payload_hex=raw_hex,
            metadata=metadata,
        )

    @staticmethod
    def _extract_lock_id(company, payload):
        if not payload:
            return None
        if company in _COMPANY_IDS_HEADER and len(payload) >= 18:
            return payload[2:18].hex()
        if company == _COMPANY_ID_TAIL_ALIGNED and len(payload) >= 16:
            return payload[-16:].hex()
        return None

    @staticmethod
    def _detect_generation(raw):
        for uuid in (raw.service_uuids or []):
            gen = _GENERATION_BY_UUID.get(_normalize_uuid(uuid))
            if gen:
                return gen
        if raw.service_data:
            for uuid in raw.service_data:
                gen = _GENERATION_BY_UUID.get(_normalize_uuid(uuid))
                if gen:
                    return gen
        return None

    def storage_schema(self):
        return None
