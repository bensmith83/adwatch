"""Medtronic Guardian CGM transmitter plugin.

Two transmitter generations, two advertisement fingerprints:

  - **Guardian Connect / Guardian Sensor** — the app's whole discovery test is
    "does the AD service-UUID list contain the 128-bit GST service
    ``b0202e40-008b-11e3-a5f3-0002a5d5c51b``?"
    (apk-ble-hunting/reports/medtronic-diabetes-guardianconnect_passive.md,
    ``…/gst/device/x0/h.java:41-56``). High confidence.
  - **Guardian 4** — the Java layer scans unfiltered and only forwards
    name + service-UUID list to Dart; the services the app builds are
    ``0xFE82`` (Medtronic's SIG-assigned member UUID, the SAKE secure channel)
    and ``0x181F`` (SIG CGM Service)
    (apk-ble-hunting/reports/medtronic-diabetes-guardian_passive.md).
    Medium-high confidence, pending a Stage-6 read of ``libapp.so``.

``0x181F`` is the vendor-agnostic SIG Continuous Glucose Monitoring service, so
it is deliberately **not** a match criterion — it is only reported as metadata
when it accompanies a Medtronic-specific UUID.

Neither generation broadcasts manufacturer data, service data or a parsed name:
glucose, calibration and serial all arrive over the SAKE/HMAC-authenticated
GATT session. Passive exposure is device-class presence only, so the identity
hash falls back to the MAC.
"""

import hashlib

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import _normalize_uuid, register_parser


# Guardian Connect / Guardian Sensor transmitter (GST) service.
GST_SERVICE_UUID = "b0202e40-008b-11e3-a5f3-0002a5d5c51b"
# Medtronic SIG member service UUID (SAKE secure channel), Guardian 4.
MEDTRONIC_SAKE_UUID = "fe82"
# SIG Continuous Glucose Monitoring service — metadata only, never a match.
CGM_SERVICE_UUID = "181f"

_GST_NORMALIZED = _normalize_uuid(GST_SERVICE_UUID)
_SAKE_NORMALIZED = _normalize_uuid(MEDTRONIC_SAKE_UUID)
_CGM_NORMALIZED = _normalize_uuid(CGM_SERVICE_UUID)


@register_parser(
    name="medtronic_cgm",
    service_uuid=(GST_SERVICE_UUID, MEDTRONIC_SAKE_UUID),
    description="Medtronic Guardian CGM transmitters (Guardian Connect / Guardian 4)",
    version="1.0.0",
    core=False,
)
class MedtronicCgmParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        advertised = {_normalize_uuid(u) for u in (raw.service_uuids or [])}
        advertised |= {_normalize_uuid(k) for k in (raw.service_data or {})}

        if _GST_NORMALIZED in advertised:
            matched = GST_SERVICE_UUID
            model = "Guardian Connect / Guardian Sensor transmitter"
        elif _SAKE_NORMALIZED in advertised:
            matched = MEDTRONIC_SAKE_UUID
            model = "Guardian 4 transmitter"
        else:
            return None

        metadata: dict = {
            "vendor": "Medtronic Diabetes",
            "model": model,
            "matched_service": matched,
        }
        if _CGM_NORMALIZED in advertised:
            metadata["has_sig_cgm_service"] = True
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        id_hash = hashlib.sha256(
            f"medtronic_cgm:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="medtronic_cgm",
            beacon_type="medtronic_cgm",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
