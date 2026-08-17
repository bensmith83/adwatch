"""Charco Neurotech CUE1 (Parkinson's vibrotactile stimulation device) plugin.

Per apk-ble-hunting/reports/charco-cue1_passive.md.

The companion app is React Native with Hermes bytecode and contains no Java
scan code, so the only statically recoverable discriminators are the device-name
tokens `CUE1`, `CUE1+` and `CUE1-`. The Nordic UART Service UUID
`6E400001-B5A3-F393-E0A9-E50E24DCC0E0` is the app's connect target and is
expected in the advertisement, but NUS is generic to every Nordic-UART
peripheral, so it is recorded as corroboration only — never a match criterion.

CUE1 is connect-to-control: battery, stimulation strength and device info are
fetched over the NUS characteristics after connecting, so no advertised
telemetry is decoded (and none is invented) here.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


NORDIC_UART_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcc0e0"

_CUE1_NAME_RE = re.compile(r"^(CUE1\+?)([\s_-]*)(.*)$", re.IGNORECASE)


@register_parser(
    name="charco_cue1",
    local_name_pattern=r"(?i)^cue1",
    description="Charco Neurotech CUE1 stimulation device",
    version="1.0.0",
    core=False,
)
class CharcoCue1Parser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        name = raw.local_name or ""
        match = _CUE1_NAME_RE.match(name)
        if not match:
            return None

        metadata: dict = {
            "vendor": "Charco Neurotech",
            "model": match.group(1).upper(),
            "device_name": name,
        }
        suffix = match.group(3).strip()
        if suffix:
            metadata["name_suffix"] = suffix

        advertised = {u.lower() for u in (raw.service_uuids or [])}
        advertised |= {k.lower() for k in (raw.service_data or {})}
        if NORDIC_UART_SERVICE_UUID in advertised:
            metadata["nordic_uart_service"] = True

        # No advertisement byte layout is documented — keep the raw bytes for the
        # explorer instead of inventing fields.
        payload = raw.manufacturer_payload
        if payload:
            metadata["payload_hex"] = payload.hex()

        id_hash = hashlib.sha256(
            f"charco_cue1:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="charco_cue1",
            beacon_type="charco_cue1",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex=(payload or b"").hex(),
            metadata=metadata,
        )
