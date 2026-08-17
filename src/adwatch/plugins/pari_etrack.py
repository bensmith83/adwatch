"""PARI eTrack Controller (eFlow rapid nebulizer adherence) BLE plugin.

Per apk-ble-hunting/reports/pari-onecf-paridev_passive.md (app
``de.pari.onecf.paridev``, bundled ``com.pari.devicekit`` SDK).

Discovery is **name-only** — the SDK uses no service-UUID or manufacturer-data
scan filter at all.  The advertised local name is
``PARI_<serial:10>_<code:4>`` (``InternalConstants.eTrackPariRegex``), and the
app pulls the 10-character middle group straight out of the name as the device
serial (``BluetoothConnectionManager.isCorrectDevice``).

No therapy/session/battery state is advertised: inhalation records sit behind a
GATT connection plus PIN+serial auth.  The passive surface is therefore
device-class detection plus a stable cleartext serial — which is also half of
the app-layer credential pair, so it is worth surfacing.

The app's secondary SpiroSense spirometer uses the stock Telit Terminal I/O
advertisement instead — see ``telit_terminal_io.py``.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

# InternalConstants.java:19 — anchored here so a longer name cannot sneak in.
PARI_NAME_PATTERN = r"^PARI_([0-9A-Za-z]{10})_([0-9A-Za-z]{4})$"

_PARI_NAME_RE = re.compile(PARI_NAME_PATTERN)


@register_parser(
    name="pari_etrack",
    local_name_pattern=PARI_NAME_PATTERN,
    description="PARI eTrack Controller nebulizer advertisements",
    version="1.0.0",
    core=False,
)
class PariEtrackParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.local_name:
            return None
        match = _PARI_NAME_RE.match(raw.local_name)
        if not match:
            return None

        serial, model_code = match.group(1), match.group(2)

        metadata: dict = {
            "vendor": "PARI",
            "product": "eTrack Controller",
            "device_name": raw.local_name,
            "serial": serial,
            "model_code": model_code,
        }

        id_hash = hashlib.sha256(
            f"pari_etrack:{serial}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="pari_etrack",
            beacon_type="pari_etrack",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
