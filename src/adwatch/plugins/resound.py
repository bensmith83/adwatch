"""GN ReSound hearing-aid plugin (vendor heuristic + ASHA service-data decode).

Per apk-ble-hunting/reports/resound-smart3d_passive.md: the Smart 3D APK is
Xamarin/.NET with the BLE constants locked inside `libmonodroid_bundle_app.so`,
so no UUID or company ID is recoverable from the app itself. Matching therefore
uses vendor-specific public signals, the same approach as `plugins/oticon.py`:

  - GN Hearing SIG company IDs 0x0067 / 0x0089
  - a `ReSound` name token

The Google ASHA UUID `0xFDF0` is **not** a match criterion: it is SIG-allocated
for all ASHA hearing aids (Oticon, Phonak, Widex, ...), so matching it here would
mis-attribute other vendors' aids to ReSound, and `plugins/oticon.py` already
emits the generic-ASHA presence record. Once a ReSound signal is present, the
spec-defined ASHA service data is decoded as enrichment:

    [0]      protocol version
    [1] bit0 side (0 = left, 1 = right); bit1 = binaural
    [2..5]   truncated HiSyncId — unique per hearing-aid pair

No live state (battery, volume, program) is broadcast per the ASHA spec.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


GN_HEARING_COMPANY_IDS = (0x0067, 0x0089)  # "GN Hearing" / "GN Hearing A/S"
ASHA_SERVICE_UUID = "fdf0"  # vendor-agnostic — enrichment only, never matched

# Exported so plugins/oticon.py can stand down on its generic-ASHA record when
# the advert already attributes the aid to GN Hearing / ReSound.
RESOUND_NAME_PATTERN = r"re[\s-]?sound"

_RESOUND_NAME_RE = re.compile(RESOUND_NAME_PATTERN, re.IGNORECASE)


def decode_asha_service_data(data: bytes) -> dict:
    """Decode the ASHA advertisement service data (spec: version/caps/HiSyncId)."""
    decoded: dict = {}
    if not data:
        return decoded
    decoded["asha_protocol_version"] = data[0]
    if len(data) >= 2:
        caps = data[1]
        decoded["side"] = "right" if caps & 0x01 else "left"
        decoded["binaural"] = bool(caps & 0x02)
        decoded["asha_capabilities"] = caps
    if len(data) >= 6:
        decoded["hi_sync_id"] = data[2:6].hex()
    return decoded


@register_parser(
    name="resound",
    company_id=list(GN_HEARING_COMPANY_IDS),
    local_name_pattern=r"(?i)re[\s-]?sound",
    description="GN ReSound hearing aids (GN Hearing CID + name heuristic)",
    version="1.0.0",
    core=False,
)
class ReSoundParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        name = raw.local_name or ""
        name_hit = bool(_RESOUND_NAME_RE.search(name))
        cid_hit = raw.company_id in GN_HEARING_COMPANY_IDS

        if not (name_hit or cid_hit):
            return None

        metadata: dict = {"vendor": "GN Hearing", "vendor_attribution": "resound"}
        if name:
            metadata["device_name"] = name
        if cid_hit:
            metadata["cid_match"] = True
            payload = raw.manufacturer_payload
            if payload:
                metadata["payload_hex"] = payload.hex()
                metadata["payload_length"] = len(payload)

        asha_data = None
        for key, value in (raw.service_data or {}).items():
            key = key.lower()
            if key == ASHA_SERVICE_UUID or key.startswith("0000fdf0-"):
                asha_data = value
                break
        if asha_data is not None:
            metadata["asha_compliant"] = True
            metadata.update(decode_asha_service_data(asha_data))

        # The HiSyncId is unique per hearing-aid pair; combining it with the
        # side yields a per-unit identity that survives MAC rotation.
        hisync = metadata.get("hi_sync_id")
        if hisync:
            basis = f"resound:{hisync}:{metadata.get('side', 'unknown')}"
        else:
            basis = f"resound:{raw.mac_address}"
        id_hash = hashlib.sha256(basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="resound",
            beacon_type="resound",
            device_class="hearing_aid",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_payload or b"").hex(),
            metadata=metadata,
        )
