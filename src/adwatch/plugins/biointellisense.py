"""BioIntelliSense BioButton / BioSticker continuous-vitals patch plugin.

Byte layout per
apk-ble-hunting/reports/biointellisense-biomobileplus-android_passive.md.

Discovery is by one of two custom 128-bit service UUIDs (the app builds one
`ScanFilter` per UUID); the manufacturer-data company ID is never validated by
the app, so it is registered here only as an extra match hint.

Report offsets are into the AD payload *including* the 2-byte company ID, so
they shift by 2 for `RawAdvertisement.manufacturer_payload`:

    payload[0]        environment   (0x02 = STAGING, else PRODUCTION)
    payload[1] bit7   busy / OTA-mutex (patch engaged with another central)
    payload[1] & 0x7F AdvertisedActivationState

No vitals are advertised — temperature/HR/respiration ride an authenticated,
encrypted GATT link. The passive leak is presence, device class, deployment
environment and lifecycle/busy state.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


BIOINTELLISENSE_COMPANY_ID = 0x08FD  # "BioIntelliSense, Inc." (SIG); unvalidated

BIO_SERVICE_UUID_PRIMARY = "278b67fe-266b-406c-bd40-25379402b58d"
BIO_SERVICE_UUID_FALLBACK = "c75c7440-6c17-4c53-886e-8cc5655798ba"
BIO_SERVICE_UUIDS = (BIO_SERVICE_UUID_PRIMARY, BIO_SERVICE_UUID_FALLBACK)

ENVIRONMENTS = {
    2: "STAGING",
    3: "PRODUCTION",
}

ACTIVATION_STATES = {
    0: "NOT_ACTIVATED",
    1: "ACTIVATED_AND_SHOULD_BE_SYNCED",
    2: "ACTIVATED_AND_SYNCED_RECENTLY",
    4: "READY_TO_REPROVISION",
}


def decode_activation_state(value: int) -> str:
    """Map the 7-bit activation-state field; 3 and >4 are RESERVED."""
    return ACTIVATION_STATES.get(value, "RESERVED")


@register_parser(
    name="biointellisense",
    company_id=BIOINTELLISENSE_COMPANY_ID,
    service_uuid=list(BIO_SERVICE_UUIDS),
    local_name_pattern=r"(?i)^bio(button|sticker)",
    description="BioIntelliSense BioButton / BioSticker vitals patch",
    version="1.0.0",
    core=False,
)
class BioIntelliSenseParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        advertised = {u.lower() for u in (raw.service_uuids or [])}
        advertised |= {k.lower() for k in (raw.service_data or {})}
        matched_uuid = next((u for u in BIO_SERVICE_UUIDS if u in advertised), None)

        name = raw.local_name or ""
        name_hit = name.lower().startswith(("biobutton", "biosticker"))
        cid_hit = raw.company_id == BIOINTELLISENSE_COMPANY_ID

        if not (matched_uuid or name_hit or cid_hit):
            return None

        metadata: dict = {"vendor": "BioIntelliSense"}
        if matched_uuid:
            metadata["service_uuid"] = matched_uuid
            metadata["hardware_generation"] = (
                "gen1" if matched_uuid == BIO_SERVICE_UUID_PRIMARY else "gen2"
            )
        if name:
            metadata["device_name"] = name
        if cid_hit:
            metadata["cid_match"] = True

        payload = raw.manufacturer_payload
        if payload:
            env_byte = payload[0]
            metadata["environment_byte"] = env_byte
            metadata["environment"] = ENVIRONMENTS.get(env_byte, "PRODUCTION")
            if len(payload) > 1:
                state_byte = payload[1]
                metadata["busy"] = bool(state_byte & 0x80)
                state_value = state_byte & 0x7F
                metadata["activation_state_value"] = state_value
                metadata["activation_state"] = decode_activation_state(state_value)

        # No stable in-payload identifier is broadcast (the name is a model
        # string), so identity falls back to the BLE address.
        id_hash = hashlib.sha256(
            f"biointellisense:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="biointellisense",
            beacon_type="biointellisense",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex=(payload or b"").hex(),
            metadata=metadata,
        )
