"""ThermoPro BBQ thermometer plugin (TP9xx / TP25 / P900 family).

Per apk-ble-hunting/reports/adsmart-thermbbq_passive.md. Distinct from
the indoor temp/humidity ``thermopro`` plugin: BBQ probes use a custom
naming convention (``TP\\d{2,3}``, ``P900``, ``Thermopro``) and three
different chipset-vendor service UUIDs across hardware generations. The
advertisement is presence-only; live temperatures arrive over GATT
notifications post-connect.

The DFU-mode aliases ``YKE-[A-Z]\\d?-DFU`` flip the device into firmware-
update mode (Nordic Secure DFU underneath).
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


# Three chipset-family service UUIDs (FFF / A3C3A55 / 1086FFF generations).
BBQ_SERVICE_UUIDS = [
    "0b863e05-ba64-4f7a-922d-007fd52dcaa9",
    "a3c3a551-b19f-435e-b89e-451b9f04284a",
    "1086fff0-3343-4817-8bb2-b32206336ce8",
]

_CHIPSET_TAG = {
    BBQ_SERVICE_UUIDS[0]: "fff",
    BBQ_SERVICE_UUIDS[1]: "a3c3a55",
    BBQ_SERVICE_UUIDS[2]: "1086fff",
}

_NAME_RE = re.compile(r"^(Thermopro|TP\d{2,3}|P900|YKE-[A-Z]\d?-DFU)$")
_DFU_RE = re.compile(r"^YKE-[A-Z]\d?-DFU$")


@register_parser(
    name="thermopro_bbq",
    service_uuid=BBQ_SERVICE_UUIDS,
    local_name_pattern=r"^(Thermopro|TP\d{2,3}|P900|YKE-[A-Z]\d?-DFU)$",
    description="ThermoPro BBQ thermometer (TP9xx / TP25 / P900 / YKE-DFU)",
    version="1.0.0",
    core=False,
)
class ThermoProBbqParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        chipset: str | None = None
        for u in BBQ_SERVICE_UUIDS:
            if u in normalized:
                chipset = _CHIPSET_TAG[u]
                break

        local_name = raw.local_name or ""
        name_match = _NAME_RE.match(local_name)

        if not (chipset or name_match):
            return None

        metadata: dict = {"vendor": "ThermoPro"}
        if chipset:
            metadata["chipset_family"] = chipset
        if name_match:
            metadata["model"] = name_match.group(1)
            metadata["device_name"] = local_name
            if _DFU_RE.match(local_name):
                metadata["dfu_mode"] = True

        id_basis = f"thermopro_bbq:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="thermopro_bbq",
            beacon_type="thermopro_bbq",
            device_class="thermometer",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
