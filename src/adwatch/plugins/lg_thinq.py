"""LG ThinQ appliance plugin (washer/dryer/fridge/AC/oven/etc.).

Per apk-ble-hunting/reports/lgeha-nuts_passive.md. ThinQ appliances
broadcast a remarkably chatty BLE record under LG's SIG-allocated CID
``0x00C4`` (196 — LG Electronics):

  - 4-byte vendor prefix (flags / device-class id, not parsed app-side)
  - 6-byte MAC address (BT or Wi-Fi — survives any OS-level address
    randomization)
  - UTF-8 product model name string (e.g. ``WashTower2 W9000``,
    ``Signature``)
  - trailing byte whose LSB is the *registered* flag (0 = not yet
    onboarded, 1 = paired to a ThinQ account)

Plus name-prefix discovery: ``AD_`` (pre-onboard SoftAP), ``LG_Smart``,
``LG_WashTower2``, ``LGE…``, ``Signature``. Per the report, this is the
highest-information passive surface in the corpus — the model name +
MAC + registered flag together fingerprint a household.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


LG_CID = 0x00C4  # 196 — LG Electronics

_NAME_RE = re.compile(r"^(AD_|ad_|LG_Smart|LG_WashTower2|LGE|Signature)")
_UNPROVISIONED_RE = re.compile(r"^(AD_|ad_)")


@register_parser(
    name="lg_thinq",
    company_id=LG_CID,
    local_name_pattern=r"^(AD_|ad_|LG_Smart|LG_WashTower2|LGE|Signature)",
    description="LG ThinQ appliances (washer/dryer/fridge/AC/oven/range/etc.)",
    version="1.0.0",
    core=False,
)
class LgThinqParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        cid_hit = raw.company_id == LG_CID
        local_name = raw.local_name or ""
        name_match = _NAME_RE.match(local_name)

        if not (cid_hit or name_match):
            return None

        metadata: dict = {"vendor": "LG"}
        if local_name:
            metadata["device_name"] = local_name

        embedded_mac: str | None = None
        if cid_hit:
            payload = raw.manufacturer_payload or b""
            # Per the report, MAC starts at offset 4 of the post-CID payload
            # (after a 4-byte vendor prefix).
            if len(payload) >= 10:
                mac_bytes = payload[4:10]
                embedded_mac = ":".join(f"{b:02X}" for b in mac_bytes)
                metadata["embedded_mac"] = embedded_mac
            # UTF-8 model name occupies bytes after the MAC up to (but not
            # including) the final flag byte.
            if len(payload) >= 12:
                model_bytes = payload[10:-1]
                try:
                    decoded = model_bytes.decode("utf-8", errors="strict")
                    if decoded.isprintable():
                        metadata["model_name"] = decoded
                except UnicodeDecodeError:
                    pass
                metadata["registered"] = bool(payload[-1] & 0x01)

        if _UNPROVISIONED_RE.match(local_name):
            metadata["provisioning_mode"] = True
        elif cid_hit and metadata.get("registered") is False:
            metadata["provisioning_mode"] = True
        else:
            metadata["provisioning_mode"] = False

        if embedded_mac:
            id_basis = f"lg_thinq:{embedded_mac}"
        elif local_name:
            id_basis = f"lg_thinq:{local_name}"
        else:
            id_basis = f"lg_thinq:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="lg_thinq",
            beacon_type="lg_thinq",
            device_class="appliance",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
