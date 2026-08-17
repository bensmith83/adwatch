"""Consumer BLE blood-glucose meters identified by advertised local name.

Per apk-ble-hunting/reports/dario-health_passive.md. The Dario app has no BLE
meter of its own (the Dario meter is audio-jack); it drives third-party meters
through the Validic Mobile SDK, which scans with a ``0x1808`` (SIG Glucose
Service) filter and then matches ``ScanRecord.getDeviceName()`` against the
regexes in the SDK's ``bluetooth.json``:

===================  ==========================================
advertised name      device
===================  ==========================================
``NiproBGM``         Nipro TRUE METRIX AIR
``Accu-Chek…``       Roche Accu-Chek Aviva Connect
``meter+NNNNNNNN``   Roche Accu-Chek Guide / Instant
``FORA MD``          ForaCare 4272 (discontinued)
===================  ==========================================

``0x1808`` is vendor-agnostic, so this plugin never matches on it — it is only
reported as metadata. The Roche Guide/Instant name embeds the meter's 8-digit
serial in the clear; it never rotates, so it is both the identity-hash basis
and a flagged privacy exposure (a persistent, health-revealing identifier
readable by any passive scanner).

No glucose readings are broadcast: readings require bonding plus RACP over
GATT (``0x2A52``/``0x2A18``).
"""

import hashlib
import re

from adwatch.models import ParseResult, RawAdvertisement
from adwatch.registry import _normalize_uuid, register_parser


# SIG Glucose Service — metadata only, deliberately not a match criterion.
GLUCOSE_SERVICE_UUID = "1808"
_GLUCOSE_NORMALIZED = _normalize_uuid(GLUCOSE_SERVICE_UUID)

GLUCOSE_METER_NAME_PATTERN = r"^(?:meter\+\d{8}|Accu-Chek|NiproBGM|FORA MD)"

_ROCHE_SERIAL_RE = re.compile(r"^meter\+(\d{8})")
_NAME_TABLE = (
    (re.compile(r"^NiproBGM"), "Nipro", "TRUE METRIX AIR"),
    (re.compile(r"^Accu-Chek"), "Roche", "Accu-Chek Aviva Connect"),
    (re.compile(r"^FORA MD"), "ForaCare", "FORA 4272"),
)


@register_parser(
    name="glucose_meters",
    local_name_pattern=GLUCOSE_METER_NAME_PATTERN,
    description="BLE blood glucose meters (Roche Accu-Chek, Nipro, ForaCare)",
    version="1.0.0",
    core=False,
)
class GlucoseMeterParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        name = raw.local_name or ""
        if not name:
            return None

        metadata: dict = {}
        serial = None

        m = _ROCHE_SERIAL_RE.match(name)
        if m:
            serial = m.group(1)
            metadata["vendor"] = "Roche"
            metadata["model"] = "Accu-Chek Guide / Instant"
            metadata["serial_number"] = serial
            metadata["serial_in_advertisement"] = True
        else:
            for pattern, vendor, model in _NAME_TABLE:
                if pattern.match(name):
                    metadata["vendor"] = vendor
                    metadata["model"] = model
                    break
            else:
                return None

        metadata["device_name"] = name
        advertised = {_normalize_uuid(u) for u in (raw.service_uuids or [])}
        if _GLUCOSE_NORMALIZED in advertised:
            metadata["has_sig_glucose_service"] = True

        if serial:
            id_basis = f"accu_chek:{serial}"
        else:
            id_basis = f"glucose_meter:{metadata['vendor']}:{raw.mac_address}"
        id_hash = hashlib.sha256(id_basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="glucose_meters",
            beacon_type="glucose_meter",
            device_class="medical",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
