"""KEF wireless speaker plugin (LSX II / LS50 / LS60 / Mu7).

Per apk-ble-hunting/reports/kef-connect_passive.md. KEF speakers
continuously advertise a 4-byte manufacturer-specific data record:

  - [0..1] vendor prefix (not exposed by the parser; either KEF's SIG CID
           encoding or a fixed sentinel)
  - [2]    projectCode — KEF model fingerprint
  - [3]    statusBitmask:
            * 0x80 isPowerOn
            * 0x10 isConnectedWithBondedDevice
            * 0x01 isInPairingMode

Plus three service UUIDs:

  - 0xFC5D — Google Fast Pair / Find My Device participation
  - 00001100-d102-11e1-9b23-00025b00a5a5 — Qualcomm GAIA service
  - baf5aa64-f6f0-bfec-43b6-8f6232654386 — KEF vendor-private

Privacy note from the report: KEF chose to expose 3 bits of speaker state
to passive observers — `isPowerOn` doubles as a household-occupancy
proxy. We surface the bits but downstream operators should treat them as
sensitive.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


KEF_VENDOR_UUID = "baf5aa64-f6f0-bfec-43b6-8f6232654386"
GAIA_SERVICE_UUID = "00001100-d102-11e1-9b23-00025b00a5a5"
FAST_PAIR_UUID = "fc5d"


@register_parser(
    name="kef",
    service_uuid=[KEF_VENDOR_UUID, GAIA_SERVICE_UUID],
    local_name_pattern=r"^KEF ",
    description="KEF wireless speakers (LSX II / LS50 II / LS60 / Mu7)",
    version="1.0.0",
    core=False,
)
class KefParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        normalized = [u.lower() for u in (raw.service_uuids or [])]
        kef_uuid_hit = KEF_VENDOR_UUID in normalized
        gaia_hit = GAIA_SERVICE_UUID in normalized
        fp_hit = FAST_PAIR_UUID in normalized or any(
            u.endswith("0000fc5d-0000-1000-8000-00805f9b34fb") for u in normalized
        )
        local_name = raw.local_name or ""
        name_hit = local_name.startswith("KEF ")

        # KEF mfr-data is exactly 4 bytes (vendor-prefix + projectCode +
        # statusBitmask) — match if the shape fits, regardless of CID.
        mfr_hit = bool(raw.manufacturer_data and len(raw.manufacturer_data) == 4)

        if not (kef_uuid_hit or gaia_hit or name_hit or (mfr_hit and (fp_hit or name_hit))):
            return None

        metadata: dict = {"vendor": "KEF"}
        if local_name:
            metadata["device_name"] = local_name
        if gaia_hit:
            metadata["gaia_service"] = True
        if fp_hit:
            metadata["fast_pair"] = True

        project: int | None = None
        if raw.manufacturer_data and len(raw.manufacturer_data) == 4:
            project = raw.manufacturer_data[2]
            status = raw.manufacturer_data[3]
            metadata["project_code"] = project
            metadata["status_byte"] = status
            metadata["is_power_on"] = bool(status & 0x80)
            metadata["is_connected_with_bonded_device"] = bool(status & 0x10)
            metadata["is_in_pairing_mode"] = bool(status & 0x01)

        if project is not None:
            id_basis = f"kef:{project:02x}:{raw.mac_address}"
        else:
            id_basis = f"kef:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="kef",
            beacon_type="kef",
            device_class="audio",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
