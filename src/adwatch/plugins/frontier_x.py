"""Fourth Frontier "Frontier X" continuous-ECG chest strap plugin.

Per apk-ble-hunting/reports/fourthfrontier-biostrip_passive.md.

The companion app (`com.fourthfrontier.biostrip`) scans unfiltered and selects
devices purely by `device.getName().contains("Frontier")` — it never touches the
scan record (zero `getManufacturerSpecificData` / `getServiceData` /
`getServiceUuids` call sites), so **no** manufacturer- or service-data layout
exists to decode and none is claimed here.

The app stores the advertised name as the device's identity token
(`CommonUtils.Biostrip_MAC_ID = bLE_Deviceinfo.getName()`), which implies the
name is per-device unique (a serial-ish suffix after the model) — so the full
name, not the MAC, is the identity-hash basis.

The custom service `9F154F00-2020-11E6-8749-0002A5D5C51B` and the SIG services
(0x180D/0x180F/0x180A) are used only post-connect; whether they appear in the
advertisement is unverified, so they are deliberately not registered.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


FRONTIER_NAME_TOKEN = "Frontier"

# "Frontier X", "FrontierX", "Frontier X2", "Frontier X3-0091", ...
_MODEL_RE = re.compile(r"Frontier\s*X(\d?)")


@register_parser(
    name="frontier_x",
    local_name_pattern=r"Frontier",
    description="Fourth Frontier Frontier X / X2 / X3 ECG chest strap",
    version="1.0.0",
    core=False,
)
class FrontierXParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        name = raw.local_name or ""
        if FRONTIER_NAME_TOKEN not in name:
            return None

        metadata: dict = {"vendor": "Fourth Frontier", "device_name": name}

        model_match = _MODEL_RE.search(name)
        if model_match:
            metadata["model"] = f"Frontier X{model_match.group(1)}"
            suffix = name[model_match.end():].strip(" -_:")
            if suffix:
                metadata["name_suffix"] = suffix
            metadata["vendor_attribution"] = "confirmed"
        else:
            # The app matches a bare "Frontier" substring, which other vendors
            # could also use — keep the record but flag it as unconfirmed.
            metadata["vendor_attribution"] = "uncertain"

        # The advertised name doubles as the app's device identity key, so it is
        # the stable per-unit token (nothing else is broadcast).
        id_hash = hashlib.sha256(f"frontier_x:{name}".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="frontier_x",
            beacon_type="frontier_x",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )
