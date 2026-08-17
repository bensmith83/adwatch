"""Tomofun Furbo pet-camera BLE advertisement plugin.

Per apk-ble-hunting/reports/tomofun-furbo_passive.md. Furbo cameras are plain
BLE peripherals whose **device name carries the entire identity** — no
manufacturer data, no service data, no service UUID in the AD record. The
companion app scans unfiltered and post-filters on seven name prefixes, each
with a length cap that bounds how much per-unit data the name carries:

    Furbo3C (<14, V3) | Furbo3 (<12, V3) | Furbo (<8, V2)
    MINICAM (uncapped, V2) | M3- (<12, V3) | M2- (<12, V2) | F2 (<5, V2)

Generation is then refined by two infix/suffix markers: a trailing ``-S3``
means the V4 GATT family, an embedded ``FW3`` means V3, otherwise the
prefix's own default applies. A ``-N`` infix marks normal (non-setup) mode.

Only the two-character ``F2`` prefix is hard-gated by its length cap here —
it is short enough to collide with unrelated devices. For the other prefixes
the cap is reported as ``matches_app_length_cap`` rather than enforced,
because the report's own example (``M3-XXXXXXX-N``, 12 chars) exceeds the
documented ``M3-`` cap.

Identity: the app derives a 12-char ID by UTF-8-decoding the *entire* raw AD
payload, stripping everything outside ``[A-Za-z0-9-]`` and taking the last 12
chars (V3/V4) or first 12 (V2). adwatch only retains the parsed local name,
not the raw AD blob, so ``app_device_id`` applies that same algorithm to the
name alone and is an approximation of the app's value. The identity hash uses
the full name when it carries a per-unit suffix of 3+ chars (durable across
MAC randomisation) and falls back to the MAC otherwise.
"""

import hashlib
import re

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import register_parser


# (prefix, app length cap or None, default generation, model)
FURBO_PREFIXES = (
    ("Furbo3C", 14, "V3", "Furbo 3C"),
    ("Furbo3", 12, "V3", "Furbo 3"),
    ("Furbo", 8, "V2", "Furbo"),
    ("MINICAM", None, "V2", "Furbo Mini Cam"),
    ("M3-", 12, "V3", "Furbo Mini 3"),
    ("M2-", 12, "V2", "Furbo Mini 2"),
    ("F2", 5, "V2", "Furbo"),
)

# `F2` is only two characters, so its cap is baked into the regex via a
# lookahead; the rest are plain anchored prefixes.
FURBO_NAME_PATTERN = r"^(?:Furbo3C|Furbo3|Furbo|MINICAM|M3-|M2-|F2(?=.{0,2}$))"

_MIN_UNIT_SUFFIX_LEN = 3
_NON_ID_CHARS = re.compile(r"[^A-Za-z0-9-]")


@register_parser(
    name="furbo",
    local_name_pattern=FURBO_NAME_PATTERN,
    description="Tomofun Furbo pet camera (Furbo / Furbo 3 / Mini, V2-V4)",
    version="1.0.0",
    core=False,
)
class FurboParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        name = raw.local_name
        if not name:
            return None

        for prefix, cap, default_gen, model in FURBO_PREFIXES:
            if name.startswith(prefix):
                break
        else:
            return None

        # Hard-gate only the ambiguous 2-char prefix.
        if prefix == "F2" and len(name) >= cap:
            return None

        remainder = name[len(prefix):]

        if name.endswith("-S3"):
            generation = "V4"
        elif "FW3" in name:
            generation = "V3"
        else:
            generation = default_gen

        unit_suffix = self._unit_suffix(remainder)

        metadata: dict = {
            "vendor": "Tomofun",
            "model": model,
            "generation": generation,
            "name_prefix": prefix,
            "device_name": name,
            "normal_mode": "-N" in name,
            "unit_suffix": unit_suffix,
            "matches_app_length_cap": cap is None or len(name) < cap,
            "app_device_id": self._app_device_id(name, generation),
        }

        if len(unit_suffix) >= _MIN_UNIT_SUFFIX_LEN:
            metadata["identity_basis"] = "name"
            stable_key = f"furbo:{name}"
        else:
            metadata["identity_basis"] = "mac"
            stable_key = None

        basis = stable_key or f"furbo:mac:{raw.mac_address}"
        id_hash = hashlib.sha256(basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="furbo",
            beacon_type="furbo",
            device_class="camera",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
            stable_key=stable_key,
        )

    @staticmethod
    def _unit_suffix(remainder: str) -> str:
        """Strip the generation/mode markers, leaving the per-unit serial."""
        s = remainder
        if s.endswith("-S3"):
            s = s[:-3]
        s = s.replace("FW3", "")
        if s.endswith("-N"):
            s = s[:-2]
        return s.strip("-")

    @staticmethod
    def _app_device_id(name: str, generation: str) -> str:
        """Approximate `BtManager.U()`'s 12-char ID using the local name.

        The app runs this over the whole raw AD payload; adwatch only keeps
        the parsed name, so this is a name-scoped approximation.
        """
        cleaned = _NON_ID_CHARS.sub("", name)
        if generation == "V2":
            return cleaned[:12]
        return cleaned[-12:]

    def storage_schema(self):
        return None
