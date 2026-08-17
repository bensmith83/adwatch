"""IQAir AirVisual plugin — identity beacon, no telemetry.

Ground truth: apk-ble-hunting report ``iqair-airvisual_passive.md``
(``com.airvisual``, Stage 4b; ``x9/d.java``,
``com/airvisual/ui/device/BluetoothDevice.java``).

IQAir devices advertise a minimal 3-byte identity payload under company ID
``0x060A`` (IQAir AG; on air ``0A 06``).  Offsets are relative to
:attr:`RawAdvertisement.manufacturer_payload`, matching the report's wire
example ``FF 0A 06 | 0A 01 01``:

===  ==========================================================
off  field
===  ==========================================================
0    product type (``x9/d.java:c()``) — selects the model code
1    ``== 1`` ⇒ ``isPairingJustWorkMode`` (pairs without a PIN)
2    pairing mode, read only when the payload length is exactly 3
===  ==========================================================

No air-quality reading is ever broadcast: PM2.5, CO2, temperature, humidity,
PM1, PM10 and fan RPM all require a GATT connection and an SDCP exchange.

**Serial number.** The advertised name is a substitution-ciphered serial.  The
report documents only part of the table and the documented part contradicts
itself (``S`` → 5 *or* 0; ``H`` → 5 while ``E`` → 6 and ``T`` → 6), so this
parser does not emit a plaintext serial — it stops at the deterministic
alphanumeric-stripped form, which is still a stable per-unit identifier and is
used to anchor the identity hash.  Completing the cipher needs the real table
from ``x9/d.java:d()``.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

IQAIR_COMPANY_ID = 0x060A

# payload[0] -> (model code, human-readable device).
PRODUCT_TYPES = {
    4: ("KLR", "IQAir air purifier (KLR)"),
    5: ("UI2", "IQAir air quality monitor (UI2)"),
    6: ("CAP", "IQAir air purifier (CAP)"),
    10: ("AVO2", "AirVisual Pro"),
    11: ("WAP", "IQAir wall-mount monitor (WAP)"),
}

# Models that carry no byte[2] fall back to a negative model-derived mode.
PAIRING_MODE_FALLBACK = {
    5: -1,    # UI2
    10: -2,   # AVO2
    11: -3,   # WAP
}

_NON_ALNUM_RE = re.compile(r"[^0-9A-Za-z]")


@register_parser(
    name="iqair",
    company_id=IQAIR_COMPANY_ID,
    description="IQAir AirVisual air quality monitors and purifiers",
    version="1.0.0",
    core=False,
)
class IQAirParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 3:
            return None
        if int.from_bytes(raw.manufacturer_data[:2], "little") != IQAIR_COMPANY_ID:
            return None

        payload = raw.manufacturer_data[2:]

        product_type = payload[0]
        model_code, device_model = PRODUCT_TYPES.get(
            product_type, ("unknown", "Unknown IQAir device")
        )
        metadata: dict = {
            "product_type": product_type,
            "model_code": model_code,
            "device_model": device_model,
            # Every reading needs a GATT/SDCP connection.
            "telemetry": False,
        }

        if len(payload) >= 2:
            metadata["pairing_just_works"] = payload[1] == 1

        if len(payload) == 3:
            metadata["pairing_mode"] = payload[2]
        elif product_type in PAIRING_MODE_FALLBACK:
            metadata["pairing_mode"] = PAIRING_MODE_FALLBACK[product_type]

        encoded_name = None
        if raw.local_name:
            stripped = _NON_ALNUM_RE.sub("", raw.local_name)
            if stripped:
                encoded_name = stripped
                metadata["encoded_name"] = stripped

        if encoded_name:
            id_hash = hashlib.sha256(
                f"iqair:{encoded_name}".encode()
            ).hexdigest()[:16]
        else:
            id_hash = hashlib.sha256(
                f"iqair:mac:{raw.mac_address}".encode()
            ).hexdigest()[:16]

        return ParseResult(
            parser_name="iqair",
            beacon_type="iqair",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata=metadata,
        )
