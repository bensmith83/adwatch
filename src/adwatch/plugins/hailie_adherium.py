"""Hailie / Adherium SmartChat inhaler-adherence sensor BLE plugin.

Per apk-ble-hunting/reports/smartinhalerlive_passive.md (app
``com.smartinhalerlive``, bundled Adherium SmartChat SDK).

The new-firmware advertising path broadcasts a fully structured
manufacturer-data element under company ID ``0x05A2`` (Adherium NZ) that the
app decodes *before connecting*.  Offsets below are within
``RawAdvertisement.manufacturer_payload`` (the report's offsets minus the
2-byte company ID):

    0        protocol version (must be 1)
    1        flags/mode  — bit7 → mode 1, bit6 → mode 2, else mode 3
    2        battery level, percent
    3-6      last-sync offset, LE uint32 seconds since 2000-01-01T00:00:00Z
             (0 ⇒ never synced)
    7-8      hardware model, LE uint16 → ``NF%04d``
    9..      serial number, ASCII

Discovery is by service UUID only: 16-bit ``0xFDFE`` (new firmware) or the
128-bit SmartChat service ``F1A42260-AA44-11E2-9E96-0800200C9A66`` (legacy).
The legacy advertising path additionally encodes the serial plus a "new dose
data pending" flag positionally, by *AD-structure index* — the raw AD
structures are not preserved by the scanner layer here, so that path is
detection-only.

Privacy note: the serial + NF model code are permanent cleartext identifiers,
so MAC randomisation does not prevent tracking; the last-sync timestamp is a
medication-adherence side channel.
"""

import hashlib
from datetime import datetime, timedelta, timezone

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

ADHERIUM_COMPANY_ID = 0x05A2  # 1442 — ADHERIUM(NZ) LIMITED
HAILIE_SIG_SERVICE_UUID = "0000fdfe-0000-1000-8000-00805f9b34fb"
HAILIE_LEGACY_SERVICE_UUID = "f1a42260-aa44-11e2-9e96-0800200c9a66"

SMARTCHAT_PROTOCOL_VERSION = 1

# `REFERENCE_YEAR = 2000` in the SDK.
_EPOCH_2000 = datetime(2000, 1, 1, tzinfo=timezone.utc)

# version + flags + battery + 4-byte sync + 2-byte model
_MIN_PAYLOAD_LEN = 9

_SIG_UUID_FORMS = {HAILIE_SIG_SERVICE_UUID, "fdfe"}


@register_parser(
    name="hailie_adherium",
    company_id=ADHERIUM_COMPANY_ID,
    service_uuid=[HAILIE_SIG_SERVICE_UUID, HAILIE_LEGACY_SERVICE_UUID],
    description="Hailie / Adherium inhaler adherence sensor advertisements",
    version="1.0.0",
    core=False,
)
class HailieParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        advertised = {u.lower() for u in (raw.service_uuids or [])}
        sig_uuid_hit = bool(advertised & _SIG_UUID_FORMS)
        legacy_uuid_hit = HAILIE_LEGACY_SERVICE_UUID in advertised
        company_hit = raw.company_id == ADHERIUM_COMPANY_ID

        if not (sig_uuid_hit or legacy_uuid_hit or company_hit):
            return None

        metadata: dict = {
            "vendor": "Adherium",
            "product": "Hailie inhaler sensor",
        }
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        if legacy_uuid_hit and not company_hit:
            metadata["generation"] = "smartchat_legacy"

        serial: str | None = None
        payload = raw.manufacturer_payload if company_hit else None

        if payload:
            version = payload[0]
            metadata["protocol_version"] = version
            if version != SMARTCHAT_PROTOCOL_VERSION:
                # The SDK rejects anything but v1 as "old firmware".
                metadata["generation"] = "legacy_firmware"
            elif len(payload) >= _MIN_PAYLOAD_LEN:
                metadata["generation"] = "smartchat_v1"

                flags = payload[1]
                metadata["flags"] = flags
                if flags & 0x80:
                    metadata["mode"] = 1
                elif flags & 0x40:
                    metadata["mode"] = 2
                else:
                    metadata["mode"] = 3

                metadata["battery_percent"] = payload[2]

                last_sync = int.from_bytes(payload[3:7], "little")
                metadata["last_sync_offset_s"] = last_sync
                metadata["never_synced"] = last_sync == 0
                if last_sync:
                    synced_at = _EPOCH_2000 + timedelta(seconds=last_sync)
                    metadata["last_sync_time"] = (
                        synced_at.isoformat().replace("+00:00", "Z")
                    )

                model_code = int.from_bytes(payload[7:9], "little")
                metadata["model_code"] = model_code
                metadata["hardware_model"] = f"NF{model_code:04d}"

                raw_serial = payload[9:].decode("ascii", errors="ignore")
                serial = "".join(c for c in raw_serial if c.isalnum())
                if serial:
                    metadata["serial"] = serial

        if serial:
            id_basis = f"hailie:{serial}"
        else:
            id_basis = f"hailie:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="hailie_adherium",
            beacon_type="hailie_adherium",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex=raw.manufacturer_data.hex() if raw.manufacturer_data else "",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
