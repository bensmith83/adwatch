"""Aranet (SAF Tehnika) CO2 / environmental monitor plugin.

Discovery per apk-ble-hunting saf-aranetcube-android_passive.md:
  * 16-bit service UUID 0xFCE0 (AranetDeviceDataProviderKt.SAF_SERVICE_UUID_STRING)
  * name prefix "Aranet" (Aranet4 / Aranet2 / Aranet Radon / Aranet☢ Nucleo)
  * company ID 0x0702 SAF Tehnika (external vendor knowledge, not in the APK) --
    presence only; the in-advert reading offset after the mfr header is not
    pinned by the report, so mfr-data readings are not decoded.

Readings (when carried as service data under the f0cd3001 UUID, original
plugin path) use the Aranet4 current-readings layout (readingParsing_es5.js
parseAranet4Reading): CO2 u16 LE | temp s16 LE x0.05 | pressure u16 LE x0.1 |
RH u8 | battery u8 | status (bits0-1: 0=error 1=green 2=yellow 3=red) |
interval u16 | age u16.

Identity: the name suffix is a stable per-device serial fragment, so hash the
full local name when it carries one; otherwise the MAC.
"""

import hashlib
import re
import struct

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

ARANET_UUID = "f0cd3001-95da-4f4b-9ac8-aa55d312af0c"
SAF_SERVICE_UUID = "fce0"
ARANET_SERVICE_UUIDS = [ARANET_UUID, SAF_SERVICE_UUID]
SAF_COMPANY_ID = 0x0702
ARANET_NAME_PATTERN = r"^Aranet"

_NAME_RE = re.compile(ARANET_NAME_PATTERN)
_SUFFIX_RE = re.compile(r"^Aranet\S*(?:\s+Radon)?\s+\S+")
_SERVICE_UUID_FORMS = {
    ARANET_UUID,
    SAF_SERVICE_UUID,
    "0000fce0-0000-1000-8000-00805f9b34fb",
}

STATUS_NAMES = {0: "error", 1: "green", 2: "yellow", 3: "red"}


def _model_from_name(name: str | None) -> str:
    if not name:
        return "Aranet"
    if name.startswith("Aranet4"):
        return "Aranet4"
    if name.startswith("Aranet2"):
        return "Aranet2"
    if name.startswith("Aranet Radon") or name.startswith("AranetRn"):
        return "Aranet Radon"
    if name.startswith("Aranet☢") or "Nucleo" in name:
        return "Aranet Nucleo"
    return "Aranet"


@register_parser(
    name="aranet4",
    company_id=SAF_COMPANY_ID,
    service_uuid=ARANET_SERVICE_UUIDS,
    local_name_pattern=ARANET_NAME_PATTERN,
    description="Aranet4/Aranet2/Radon/Nucleo (SAF Tehnika) sensors",
    version="1.1.0",
    core=False,
)
class Aranet4Parser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        name = raw.local_name or ""
        data = (raw.service_data or {}).get(ARANET_UUID)
        matched = (
            bool(_NAME_RE.match(name))
            or bool(_SERVICE_UUID_FORMS.intersection(raw.service_uuids or []))
            or raw.company_id == SAF_COMPANY_ID
            or data is not None
        )
        if not matched:
            return None

        metadata: dict = {"model": _model_from_name(name)}
        payload = b""
        if data and len(data) >= 13:
            payload = data
            status = data[8] & 0x03
            metadata.update({
                "co2_ppm": struct.unpack_from("<H", data, 0)[0],
                "temperature_c": struct.unpack_from("<h", data, 2)[0] / 20.0,
                "pressure_hpa": struct.unpack_from("<H", data, 4)[0] / 10.0,
                "humidity": data[6],
                "battery": data[7],
                "status": STATUS_NAMES[status],
                "interval_s": struct.unpack_from("<H", data, 9)[0],
                "age_s": struct.unpack_from("<H", data, 11)[0],
            })
        elif raw.company_id == SAF_COMPANY_ID and raw.manufacturer_payload:
            payload = raw.manufacturer_payload

        if _SUFFIX_RE.match(name):
            id_basis = f"aranet:{name}"
        else:
            id_basis = raw.mac_address
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="aranet4",
            beacon_type="aranet4",
            device_class="sensor",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
