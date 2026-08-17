"""PetSafe / Radio Systems Corp BLE advertisement plugin.

Per apk-ble-hunting/reports/net-petsafe-platform_passive.md. PetSafe stores
every BLE UUID as a base64-encoded ASCII string inside
``libps-ble-provisioner-native-lib.so`` and fetches them through JNI getters,
so nothing is visible from the Java tree. The decoded UUIDs cover three
device families:

* **Collar** — Data Transfer ``a2efa8a6-74b0-11ed-a799-f34a64caa2bf`` and
  Telemetry ``492f9947-52d2-41f5-b59c-313e96e48ec0``. The first is a v1
  (time-based) UUID, so its embedded timestamp dates the collar generation.
* **SDT** (Smart Dog Trainer / Smart Door) —
  ``e7add780-b042-4876-aae1-112855353cc1``.
* **RSC sentinel** — ``52534300-6822-5570-6886-123456789abc``, whose first
  four bytes spell ``RSC\\0`` in ASCII. *Any* UUID with that prefix is a Radio
  Systems Corp product (PetSafe / Invisible Fence / Innotek).

The registry can only match exact UUIDs, so the ``52534300-`` prefix is
checked inside ``parse()``; devices carrying an unlisted RSC-prefixed UUID are
reached through the Radio Systems SIG company ID 0x01FE instead. (A device
that advertises *only* an unlisted RSC UUID and no 0x01FE manufacturer data
cannot be reached by the registry at all — an inherent exact-match limit.)

The advertisement is identity-only: telemetry (battery, sensors) is delivered
post-connect on the Telemetry service. The MAC is the only per-unit
discriminator, and these devices are outdoor-deployed with likely-public
addresses.
"""

import datetime
import hashlib
import uuid as _uuid

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import _normalize_uuid, register_parser


RADIO_SYSTEMS_COMPANY_ID = 0x01FE  # SIG: Radio Systems Corporation

COLLAR_DATA_TRANSFER_UUID = "a2efa8a6-74b0-11ed-a799-f34a64caa2bf"
COLLAR_TELEMETRY_UUID = "492f9947-52d2-41f5-b59c-313e96e48ec0"
SDT_SERVICE_UUID = "e7add780-b042-4876-aae1-112855353cc1"
RSC_SENTINEL_UUID = "52534300-6822-5570-6886-123456789abc"

PETSAFE_SERVICE_UUIDS = (
    COLLAR_DATA_TRANSFER_UUID,
    COLLAR_TELEMETRY_UUID,
    SDT_SERVICE_UUID,
    RSC_SENTINEL_UUID,
)

# normalized uuid -> (family, service role)
_ROLE_BY_UUID = {
    _normalize_uuid(COLLAR_DATA_TRANSFER_UUID): ("collar", "collar_data_transfer"),
    _normalize_uuid(COLLAR_TELEMETRY_UUID): ("collar", "collar_telemetry"),
    _normalize_uuid(SDT_SERVICE_UUID): ("sdt", "sdt_commands"),
    _normalize_uuid(RSC_SENTINEL_UUID): ("sentinel", "rsc_sentinel"),
}

# bytes 0-3 == b"RSC\x00"
RSC_UUID_PREFIX = "52534300-"

_DEVICE_CLASS_BY_FAMILY = {
    "collar": "pet_tracker",
    "sdt": "access_control",
    "sentinel": "pet_tracker",
    "unknown": "pet_tracker",
}

# UUID v1 epoch: 1582-10-15, counted in 100 ns ticks.
_UUID_V1_EPOCH = datetime.datetime(1582, 10, 15, tzinfo=datetime.timezone.utc)


@register_parser(
    name="petsafe",
    company_id=RADIO_SYSTEMS_COMPANY_ID,
    service_uuid=list(PETSAFE_SERVICE_UUIDS),
    description="PetSafe / Radio Systems Corp collar, Smart Dog Trainer, Smart Door",
    version="1.0.0",
    core=False,
)
class PetSafeParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        advertised = [_normalize_uuid(u) for u in (raw.service_uuids or [])]

        family = None
        role = None
        matched_uuid = None
        for u in advertised:
            hit = _ROLE_BY_UUID.get(u)
            if hit:
                family, role = hit
                matched_uuid = u
                break

        rsc_signature = any(u.startswith(RSC_UUID_PREFIX) for u in advertised)
        has_company = raw.company_id == RADIO_SYSTEMS_COMPANY_ID

        if family is None and not (rsc_signature or has_company):
            return None

        if family is None:
            family = "unknown"

        metadata: dict = {
            "vendor": "Radio Systems Corp (PetSafe)",
            "family": family,
            "rsc_signature": rsc_signature,
        }
        if role:
            metadata["service_role"] = role
        if matched_uuid:
            metadata["service_uuid"] = matched_uuid
            minted = self._uuid_v1_date(matched_uuid)
            if minted:
                metadata["uuid_minted"] = minted
        if has_company:
            metadata["company_id_hex"] = f"0x{RADIO_SYSTEMS_COMPANY_ID:04X}"
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        id_hash = hashlib.sha256(
            f"petsafe:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="petsafe",
            beacon_type="petsafe",
            device_class=_DEVICE_CLASS_BY_FAMILY[family],
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_payload or b"").hex(),
            metadata=metadata,
        )

    @staticmethod
    def _uuid_v1_date(u: str) -> str | None:
        """Return the mint date of a v1 (time-based) UUID, else None."""
        try:
            parsed = _uuid.UUID(u)
        except ValueError:
            return None
        if parsed.version != 1:
            return None
        try:
            when = _UUID_V1_EPOCH + datetime.timedelta(microseconds=parsed.time // 10)
        except (OverflowError, ValueError):
            return None
        return when.date().isoformat()

    def storage_schema(self):
        return None
