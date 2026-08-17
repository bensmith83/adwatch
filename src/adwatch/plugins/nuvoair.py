"""NuvoAir AirNext home spirometer BLE plugin.

Per apk-ble-hunting/reports/nuvoair-aria_passive.md.

Two hardware generations share the discovery surface:

  - **AOS / ATS2019** — advertises a 4-byte *service data* blob under UUID
    ``0000ABCD-0000-1000-8000-00805F9B34FB`` (the SDK also reads it from the
    ``00001530`` SIG-base UUID): ``[fwMajor, fwMinor, numSessions, flags]``.
    ``flags`` bit0 = ``rtcNotSet`` (device clock unconfigured), bit1 =
    ``spacer``.  A Nordic Semiconductor (``0x0059``) manufacturer-data block
    is the fallback encoding, whose first byte is ``numSessions``.
  - **AirNext (legacy)** — service-UUID discovery only
    (``00002000-0000-1000-8000-00805F9B34FB``), no advertised state.

``numSessions`` is the count of spirometry tests buffered on the device — a
cleartext usage side channel that increments on every breath test.

DFU/bootloader state is inferable by name: ``AIR-DFU`` (AirNext bootloader)
or ``DfuTarg`` (AOS bootloader).  ``DfuTarg`` is the stock Nordic bootloader
name, so it is only honoured alongside the Nordic legacy DFU service UUID and
is deliberately NOT a registration criterion on its own.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

# Nordic Semiconductor ASA — AOS_DATA_KEY = 89 in the app.
NORDIC_COMPANY_ID = 0x0059

# AOS / ATS2019 generation (the report's "OLD" scan filter, but the
# generation that actually broadcasts state).
NUVOAIR_AOS_SERVICE_UUID = "0000abcd-0000-1000-8000-00805f9b34fb"
# AirNext generation (the report's "NEW" scan filter) — discovery only.
NUVOAIR_NEW_SERVICE_UUID = "00002000-0000-1000-8000-00805f9b34fb"
# SDK fallback service-data key (SIG-base form of the DFU 16-bit value).
NUVOAIR_DFU_BASE_UUID = "00001530-0000-1000-8000-00805f9b34fb"
# Nordic legacy DFU (bootloader) service.
NORDIC_LEGACY_DFU_UUID = "00001530-1212-efde-1523-785feabcd123"

# The app treats firmware 1.32 as the required baseline.
REQUIRED_FW_MAJOR = 1
REQUIRED_FW_MINOR = 32

_BT_BASE_SUFFIX = "-0000-1000-8000-00805f9b34fb"

_SERVICE_DATA_KEYS = ("abcd", "1530")


def _uuid_forms(uuid: str) -> set[str]:
    """Both the short and 128-bit lowercase spellings of a SIG-base UUID."""
    full = uuid.lower()
    forms = {full}
    if full.endswith(_BT_BASE_SUFFIX) and full.startswith("0000"):
        forms.add(full[4:8])
    return forms


_AOS_UUID_FORMS = _uuid_forms(NUVOAIR_AOS_SERVICE_UUID)
_NEW_UUID_FORMS = _uuid_forms(NUVOAIR_NEW_SERVICE_UUID)
_DFU_BASE_UUID_FORMS = _uuid_forms(NUVOAIR_DFU_BASE_UUID)


def _service_data_blob(raw: RawAdvertisement) -> bytes | None:
    """Return the NuvoAir service-data payload, under either advertised key."""
    if not raw.service_data:
        return None
    for key, value in raw.service_data.items():
        k = key.lower()
        if k in _AOS_UUID_FORMS or k in _DFU_BASE_UUID_FORMS:
            return value
    return None


@register_parser(
    name="nuvoair",
    service_uuid=[NUVOAIR_AOS_SERVICE_UUID, NUVOAIR_NEW_SERVICE_UUID],
    local_name_pattern=r"^AIR-DFU$",
    description="NuvoAir AirNext spirometer advertisements",
    version="1.0.0",
    core=False,
)
class NuvoAirParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        advertised = {u.lower() for u in (raw.service_uuids or [])}
        aos_uuid_hit = bool(advertised & _AOS_UUID_FORMS)
        new_uuid_hit = bool(advertised & _NEW_UUID_FORMS)
        nordic_dfu_uuid_hit = NORDIC_LEGACY_DFU_UUID in advertised

        local_name = raw.local_name or ""
        air_dfu_hit = local_name == "AIR-DFU"
        dfutarg_hit = local_name == "DfuTarg" and nordic_dfu_uuid_hit

        blob = _service_data_blob(raw)

        if not (aos_uuid_hit or new_uuid_hit or blob is not None
                or air_dfu_hit or dfutarg_hit):
            return None

        metadata: dict = {
            "vendor": "NuvoAir",
            "product": "AirNext spirometer",
        }
        if local_name:
            metadata["device_name"] = local_name

        # Generation: anything that speaks the AOS advertising shape is AOS;
        # the bare "NEW" scan-filter UUID and the AIR-DFU bootloader name are
        # the legacy AirNext generation.
        if blob is not None or aos_uuid_hit or dfutarg_hit:
            metadata["generation"] = "aos"
        else:
            metadata["generation"] = "airnext"

        if air_dfu_hit or dfutarg_hit:
            metadata["dfu_mode"] = True

        num_sessions: int | None = None

        # Primary channel: the 4-byte AOS service-data blob.
        if blob is not None and len(blob) == 4:
            major, minor, sessions, flags = blob[0], blob[1], blob[2], blob[3]
            metadata["firmware_major"] = major
            metadata["firmware_minor"] = minor
            metadata["firmware_version"] = f"{major}.{minor:02d}"
            metadata["is_required_version"] = (
                major == REQUIRED_FW_MAJOR and minor == REQUIRED_FW_MINOR
            )
            metadata["flags"] = flags
            metadata["rtc_not_set"] = bool(flags & 0x01)
            metadata["spacer_flag"] = bool(flags & 0x02)
            num_sessions = sessions
            metadata["num_sessions_source"] = "service_data"
        # Fallback: Nordic manufacturer data, first byte = numSessions.
        elif raw.company_id == NORDIC_COMPANY_ID and raw.manufacturer_payload:
            num_sessions = raw.manufacturer_payload[0]
            metadata["num_sessions_source"] = "manufacturer_data"

        if num_sessions is not None:
            metadata["num_sessions"] = num_sessions
            metadata["has_advertised_sessions"] = num_sessions > 0

        if blob is not None:
            payload_hex = blob.hex()
        elif raw.manufacturer_data:
            payload_hex = raw.manufacturer_data.hex()
        else:
            payload_hex = ""

        # MAC is the only stable identifier the device broadcasts — the
        # advertisement carries no serial, and the report finds no evidence
        # of RPA rotation.
        id_hash = hashlib.sha256(
            f"nuvoair:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="nuvoair",
            beacon_type="nuvoair",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex=payload_hex,
            metadata=metadata,
        )

    def storage_schema(self):
        return None
