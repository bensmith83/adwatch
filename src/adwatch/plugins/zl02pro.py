"""ZL02PRO / DaFit-family BT-calling smartwatch parser.

"ZL02PRO" is a white-label round-face BT-calling smartwatch built on Realtek
RTL8763EWE and paired via the **DaFit** companion app. The advertisement
carries a service data entry under UUID `0xFEEA` whose first three bytes
spell ASCII "DKR" -- a proprietary framing used by the DaFit firmware.

Both the CID (0xF0EF) and the FEEA service UUID are **not** SIG-registered.
We match by local-name prefix or by the DKR magic in FEEA service data.

See `docs/protocols/zl02pro-dafit.md` for details.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


DAFIT_SERVICE_DATA_UUID = "feea"
DAFIT_HEADER = b"DKR"  # 0x44 0x4B 0x52
_NAME_RE = re.compile(r"^ZL0[0-9A-Z]{2,}")


@register_parser(
    name="zl02pro",
    service_uuid=DAFIT_SERVICE_DATA_UUID,
    local_name_pattern=r"^ZL0[0-9A-Z]{2,}",
    description="ZL02PRO / DaFit-family BT-calling smartwatch",
    version="1.0.0",
    core=False,
)
class ZL02ProParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        name = raw.local_name or ""
        name_match = _NAME_RE.match(name)

        svc = (raw.service_data or {}).get(DAFIT_SERVICE_DATA_UUID)
        dkr_match = bool(svc and svc.startswith(DAFIT_HEADER))

        if not name_match and not dkr_match:
            return None

        metadata: dict = {}
        if name:
            metadata["device_name"] = name
        if dkr_match:
            metadata["protocol"] = "DKR"
            metadata["protocol_payload_hex"] = svc[len(DAFIT_HEADER):].hex()

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:zl02pro".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="zl02pro",
            beacon_type="zl02pro",
            device_class="smartwatch",
            identifier_hash=id_hash,
            raw_payload_hex=svc.hex() if svc else "",
            metadata=metadata,
        )
