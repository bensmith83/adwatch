"""Trezor hardware-wallet plugin (Trezor Safe family).

Per apk-ble-hunting/reports/trezor-suite_passive.md (io.trezor.suite).

Trezor Safe devices advertise the open-source THP (Trezor Hardware Protocol)
service UUID ``8c000001-a59b-4d58-a9ad-073df69fa1b1`` together with a
**device-class-only** local name drawn from a documented set (``Trezor Safe 3``
… ``Trezor Safe 7 Freedom Edition``). There is no manufacturer data, no service
data and — deliberately — no per-unit serial anywhere in the broadcast: every
Safe 7 in the world advertises byte-identically.

That makes this an identity/presence parser. The privacy note from the report
still applies: the UUID + name pair instantly outs the device as a hardware
crypto wallet, which is a high-value-asset signal for a passive observer. The
only per-unit differentiator is the BLE MAC, so that is the identity basis.

The Trezor SIG company ID (0x0F29, "Trezor Company s.r.o.") is registered as a
match criterion for forward-compatibility; any payload seen under it is
surfaced undecoded rather than dropped.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import _normalize_uuid, register_parser


TREZOR_SERVICE_UUID = "8c000001-a59b-4d58-a9ad-073df69fa1b1"
TREZOR_NAME_RE = r"^Trezor\b"
TREZOR_COMPANY_ID = 0x0F29

_TREZOR_UUID_NORM = _normalize_uuid(TREZOR_SERVICE_UUID)
_MODEL_RE = re.compile(r"(?i)^(Trezor Safe \d+)(?:\s+(Freedom Edition))?$")


@register_parser(
    name="trezor_wallet",
    company_id=TREZOR_COMPANY_ID,
    service_uuid=TREZOR_SERVICE_UUID,
    local_name_pattern=TREZOR_NAME_RE,
    description="Trezor hardware wallets (Trezor Safe 3 / 5 / 7)",
    version="1.0.0",
    core=False,
)
class TrezorWalletParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        uuid_hit = any(
            _normalize_uuid(u) == _TREZOR_UUID_NORM
            for u in (raw.service_uuids or [])
        )
        name = (raw.local_name or "").strip()
        name_hit = bool(name and re.search(TREZOR_NAME_RE, name))
        cid_hit = raw.company_id == TREZOR_COMPANY_ID

        if not (uuid_hit or name_hit or cid_hit):
            return None

        metadata: dict = {
            "vendor": "Trezor",
            "service_uuid_match": uuid_hit,
        }

        if name:
            metadata["device_name"] = name
            m = _MODEL_RE.match(name)
            if m:
                metadata["model"] = m.group(1)
                metadata["freedom_edition"] = m.group(2) is not None

        # The report says Trezor emits no manufacturer data; keep anything that
        # does turn up visible for the Protocol Explorer instead of dropping it.
        if cid_hit:
            metadata["company_id"] = raw.company_id
            payload = raw.manufacturer_payload
            if payload:
                metadata["payload_hex"] = payload.hex()

        return ParseResult(
            parser_name="trezor_wallet",
            beacon_type="trezor_wallet",
            device_class="hardware_wallet",
            identifier_hash=hashlib.sha256(
                f"trezor:{raw.mac_address}".encode()
            ).hexdigest()[:16],
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
