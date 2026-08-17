"""Empatica EmbracePlus (seizure-monitoring wristband) plugin.

Byte layout per apk-ble-hunting/reports/empatica-healthmonitor-epilepsy_passive.md.

The EpiMonitor app scans unfiltered and gates in software on:
  - local name containing "Embrace", and
  - a manufacturer-data block of at least 24 bytes.

The company ID is never checked by the app (`valueAt(0)`); Empatica's
SIG-assigned ID 0x02D1 is registered here as an extra match criterion, but
decoding never requires it. Offsets below are into the block *after* the 2-byte
company ID — i.e. straight into `RawAdvertisement.manufacturer_payload`:

    [0..6]    unparsed header
    [7..16]   ASCII serial (10 chars); serial[0] selects the model and the
              rest selects the hardware variant
    [17..18]  unparsed
    [19] & 3  pairing mode (0/1/2 valid)
    [20]      quick-pairing mode (0/1/3 valid)

The plaintext serial is broadcast in every advertisement, so it is a stable
identity token that survives MAC rotation — that is the identity-hash basis.
No physiological data (EDA/BVP/SpO2/seizure state) is advertised; it rides the
encrypted GATT link.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


EMPATICA_COMPANY_ID = 0x02D1  # "Empatica Srl" (SIG); not validated by the app
EMPATICA_SERVICE_UUID = "3ea00001-e0e2-e4ff-9069-6a7f0ae28705"

SERIAL_OFFSET = 7
SERIAL_LENGTH = 10
MIN_PAYLOAD_LEN = 24
PAIRING_MODE_OFFSET = 19
QUICK_PAIRING_OFFSET = 20

VALID_PAIRING_MODES = (0, 1, 2)
VALID_QUICK_PAIRING_MODES = (0, 1, 3)

MODELS = {
    "1": "EMBRACE1",
    "2": "EMBRACE2",
    "3": "EMBRACE_PLUS",
    "4": "EMBRACE_PLUS",
}

_MINI_RE = re.compile(r"^3YM.{2}YY.*$")
_V2_RE = re.compile(r"^3C.*$")


def decode_model(serial: str) -> str:
    """Model from the serial's first character (z8/EnumC6622d.java:54-67)."""
    if not serial:
        return "UNKNOWN"
    return MODELS.get(serial[0], "UNKNOWN")


def decode_variant(serial: str) -> str | None:
    """Hardware variant — computed only for EMBRACE_PLUS serials ('3'/'4')."""
    if decode_model(serial) != "EMBRACE_PLUS":
        return None
    if "4" in serial or _MINI_RE.match(serial):
        return "EMBRACE_MINI"
    if _V2_RE.match(serial):
        return "EMBRACE_PLUS_V2"
    return "EMBRACE_PLUS"


@register_parser(
    name="empatica",
    company_id=EMPATICA_COMPANY_ID,
    service_uuid=EMPATICA_SERVICE_UUID,
    local_name_pattern=r"(?i)embrace",
    description="Empatica EmbracePlus seizure-monitoring wristband",
    version="1.0.0",
    core=False,
)
class EmpaticaParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        name = raw.local_name or ""
        name_hit = "embrace" in name.lower()
        cid_hit = raw.company_id == EMPATICA_COMPANY_ID
        advertised = {u.lower() for u in (raw.service_uuids or [])}
        advertised |= {k.lower() for k in (raw.service_data or {})}
        uuid_hit = EMPATICA_SERVICE_UUID in advertised

        if not (name_hit or cid_hit or uuid_hit):
            return None

        metadata: dict = {"vendor": "Empatica"}
        if name:
            metadata["device_name"] = name
        if cid_hit:
            metadata["cid_match"] = True
        if uuid_hit:
            metadata["service_uuid_match"] = True

        serial = None
        payload = raw.manufacturer_payload
        if payload:
            metadata["payload_length"] = len(payload)
        if payload and len(payload) >= MIN_PAYLOAD_LEN:
            chunk = payload[SERIAL_OFFSET:SERIAL_OFFSET + SERIAL_LENGTH]
            try:
                decoded = chunk.decode("ascii")
            except UnicodeDecodeError:
                decoded = None
            if decoded and decoded.isprintable():
                serial = decoded
                metadata["serial"] = serial
                metadata["model"] = decode_model(serial)
                variant = decode_variant(serial)
                if variant:
                    metadata["hardware_variant"] = variant

            pairing = payload[PAIRING_MODE_OFFSET] & 0x03
            quick = payload[QUICK_PAIRING_OFFSET]
            metadata["pairing_mode"] = pairing
            metadata["pairing_mode_valid"] = pairing in VALID_PAIRING_MODES
            metadata["quick_pairing_mode"] = quick
            metadata["quick_pairing_mode_valid"] = quick in VALID_QUICK_PAIRING_MODES

        # The plaintext serial is stable across MAC rotation; prefer it.
        basis = f"empatica:{serial}" if serial else f"empatica:{raw.mac_address}"
        id_hash = hashlib.sha256(basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="empatica",
            beacon_type="empatica",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex=(payload or b"").hex(),
            metadata=metadata,
        )
