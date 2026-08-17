"""iTENS (Brighteye Innovations) TENS pain-therapy device plugin.

Per apk-ble-hunting/reports/brighteye-itens_passive.md.

Unusually for this category, iTENS is **broadcast-rich**: the app decodes the
advertised manufacturer payload without connecting.

Discovery fingerprint (`f0/h.java:40-93`) — a scan result is an iTENS iff ALL
three hold:

  1. manufacturer data under company ID **12357 (0x3045)**, length >= 1
  2. the advertised service-UUID list contains **0xFFF0**
  3. the advertised service-UUID list contains **0xFFB0**

All three are enforced. 0x3045 is *not* a SIG-assigned company ID (it does not
appear in ``_bt_company_ids.py``), so it is a squatted value and carries less
weight on its own — the UUID pair is load-bearing, and 0xFFF0 alone is a
generic Chinese-module service shared with several unrelated plugins.

Manufacturer payload — two shapes (`f0/g.java:2485-2520`). Note the offsets are
relative to the payload *after* the company ID, because Android's
``getManufacturerSpecificData(id)`` already strips it — the same slice as
``RawAdvertisement.manufacturer_payload``, so no offset shift is needed:

  **Format A — 7-byte little-endian binary frame** (selected when the
  proprietary service 0x5000 is also advertised)::

      [0:2] uint16 LE  field L
      [2]   uint8      field Q
      [3]   uint8      field P
      [4]   uint8      field N
      [5]   uint8      field O
      [6]   uint8      field M

  The app's field names are single-letter obfuscated identifiers. The *layout*
  is high-confidence; the *semantics* are not recoverable, so the fields keep
  their obfuscated names and ``field_semantics`` is reported as ``unknown``
  rather than guessing at intensity/mode/channel meanings.

  **Format B — ASCII ``EM<digits>``**: the payload is read as a string and
  matched against ``(?<=EM)\\d+``; the digits are a model/device id.

Full stimulation state and intensity control require connecting to the 0x5000
service; only the above is broadcast.

Privacy: the ``EM<digits>`` id (and plausibly the stable-looking 16-bit field L)
gives a per-device fingerprint readable without connecting, and presence alone
discloses a TENS pain-therapy device. Flagged ``sensitive=True``.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


# Squatted (not SIG-assigned) company ID; raw bytes `45 30` little-endian.
ITENS_COMPANY_ID = 0x3045

_FFF0 = "fff0"
_FFB0 = "ffb0"
_PROPRIETARY = "5000"
_BT_BASE = "-0000-1000-8000-00805f9b34fb"

_EM_RE = re.compile(r"EM(\d+)")


def _has_uuid(normalized: set, short: str) -> bool:
    return short in normalized or f"0000{short}{_BT_BASE}" in normalized


@register_parser(
    name="itens",
    company_id=ITENS_COMPANY_ID,
    description="iTENS TENS unit (CID 0x3045 + FFF0/FFB0, broadcast state)",
    version="1.0.0",
    core=False,
)
class ITensParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if raw.company_id != ITENS_COMPANY_ID:
            return None

        payload = raw.manufacturer_payload or b""
        if len(payload) < 1:
            return None

        normalized = {u.lower() for u in (raw.service_uuids or [])}
        if not (_has_uuid(normalized, _FFF0) and _has_uuid(normalized, _FFB0)):
            return None
        proprietary = _has_uuid(normalized, _PROPRIETARY)

        metadata: dict = {
            "vendor": "iTENS",
            "product": "iTENS TENS unit",
            "company_id": ITENS_COMPANY_ID,
            "proprietary_service": proprietary,
            "mfr_payload_hex": payload.hex(),
            "sensitive": True,
            "sensitive_category": "pain_therapy",
        }
        if raw.local_name:
            # Parsed by the app but explicitly not used for matching.
            metadata["device_name"] = raw.local_name

        em_id = self._ascii_em_id(payload)
        if proprietary and len(payload) >= 7:
            self._decode_binary(payload, metadata)
        elif em_id is not None:
            metadata["payload_format"] = "ascii_em"
            metadata["model_id"] = em_id
        elif len(payload) >= 7:
            self._decode_binary(payload, metadata)
        else:
            metadata["payload_format"] = "unknown"

        # The EM<digits> id is a persistent broadcast identifier; field L only
        # *appears* stable per unit, so it is not trusted for identity.
        if metadata.get("payload_format") == "ascii_em":
            id_basis = f"itens:em{metadata['model_id']}"
            metadata["identity_basis"] = "em_id"
        else:
            id_basis = f"itens:{raw.mac_address}"
            metadata["identity_basis"] = "mac"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="itens",
            beacon_type="itens",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    @staticmethod
    def _ascii_em_id(payload: bytes) -> int | None:
        try:
            text = payload.decode("ascii")
        except UnicodeDecodeError:
            return None
        m = _EM_RE.search(text)
        return int(m.group(1)) if m else None

    @staticmethod
    def _decode_binary(payload: bytes, metadata: dict) -> None:
        metadata["payload_format"] = "binary"
        metadata["field_l"] = int.from_bytes(payload[0:2], "little")
        metadata["field_q"] = payload[2]
        metadata["field_p"] = payload[3]
        metadata["field_n"] = payload[4]
        metadata["field_o"] = payload[5]
        metadata["field_m"] = payload[6]
        # Obfuscated single-letter names in the APK — do not invent meanings.
        metadata["field_semantics"] = "unknown"

    def storage_schema(self):
        return None
