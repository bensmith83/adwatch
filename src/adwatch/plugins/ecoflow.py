"""EcoFlow portable power station plugin.

Byte layout verified against ``apk-ble-hunting`` report ``ecoflow_passive.md``
(decompiled ``com.ecoflow``, Stage 4b).  The report gives offsets relative to
**M**, the index of the manufacturer-data AD *length* byte.  The SIG company ID
sits at ``M+2..M+3``, and :attr:`RawAdvertisement.manufacturer_payload` strips
those two bytes, so::

    payload[j]  ==  report offset M+4+j

Fields (report → payload index):

===========  =============  =================================================
report off   payload index  field
===========  =============  =================================================
M+4          0              protocol/version byte (``>= 0xA1`` ⇒ protocol V2)
M+5..M+20    1..16          16-byte ASCII serial number
M+21         17             bits0-6 state-of-charge %, bit7 dormancy
M+22         18             model byte / OTA (bits7-6 upgrade, bits5-0 config)
M+23         19             bit2 charging, ``(x & 3) == 1`` ⇒ sleeping
M+24         20             config/pairing state (V1 families)
M+26         22             security capability bits
===========  =============  =================================================

The app also installs a scan filter on service-data UUID ``0xFFF6``, but no
code path decodes that payload and ``0xFFF6`` is the Matter commissionable
UUID, so it is deliberately *not* registered here — it would steal every
Matter advert.
"""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

ECOFLOW_COMPANY_ID = 0xB5B5
# All three IDs the app installs scan filters for
# (EFSmartDeviceCenterManager.java:105-107).
ECOFLOW_COMPANY_IDS = (0xB5B5, 0xA4A8, 0x0BA9)

# Exact local name used by the telemetry-free "home" device class
# (cn/e.java:165, el/i.java:142-146) — productType 1001, model 1.
ECO_HOME_NAME = "ECO_HOME"
ECO_HOME_PRODUCT_TYPE = 1001

# Version byte gate for the V2 advertisement (bn/c.java:130).
PROTOCOL_V2_MIN = 0xA1

SERIAL_PREFIX_MAP = {
    "R331": "DELTA 2", "R335": "DELTA 2",
    "R351": "DELTA 2 Max", "R354": "DELTA 2 Max",
    "P231": "DELTA 3", "D3N1": "DELTA 3 Classic",
    "DCA": "DELTA Pro", "DCF": "DELTA Pro", "DCK": "DELTA Pro",
    "MR51": "DELTA Pro 3", "Y711": "DELTA Pro Ultra",
    "R601": "RIVER 2", "R603": "RIVER 2",
    "R611": "RIVER 2 Max", "R613": "RIVER 2 Max",
    "R631": "RIVER 3 Plus", "R634": "RIVER 3 Plus",
    "HW51": "PowerStream", "HD31": "Smart Home Panel 2",
    "DB": "DELTA mini",
}


@register_parser(
    name="ecoflow",
    company_id=ECOFLOW_COMPANY_IDS,
    local_name_pattern=r"^(EF-|ECO_HOME$)",
    description="EcoFlow power stations",
    version="1.1.0",
    core=False,
)
class EcoFlowParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.manufacturer_data or len(raw.manufacturer_data) < 4:
            if raw.local_name == ECO_HOME_NAME:
                return self._parse_eco_home(raw)
            return None

        company_id = int.from_bytes(raw.manufacturer_data[:2], "little")
        if company_id not in ECOFLOW_COMPANY_IDS:
            return None

        payload = raw.manufacturer_data[2:]
        return self._parse_payload(raw, payload, company_id)

    def _parse_eco_home(self, raw) -> ParseResult:
        """`ECO_HOME` devices are identified by name only — no telemetry."""
        return ParseResult(
            parser_name="ecoflow",
            beacon_type="ecoflow_home",
            device_class="power",
            identifier_hash=self._mac_hash(raw),
            raw_payload_hex="",
            metadata={
                "name_only": True,
                "product_type_code": ECO_HOME_PRODUCT_TYPE,
                "device_model": "EcoFlow Smart Home",
            },
        )

    def _parse_payload(self, raw, payload, company_id):
        protocol_version = payload[0]
        metadata = {
            "company_id": company_id,
            "protocol_version": protocol_version,
            "protocol_v2": protocol_version >= PROTOCOL_V2_MIN,
        }

        serial = None
        if len(payload) >= 17:
            serial_bytes = payload[1:17]
            try:
                serial = serial_bytes.decode("ascii").rstrip("\x00").rstrip()
            except UnicodeDecodeError:
                serial = serial_bytes.hex()
            metadata["serial_number"] = serial
            metadata["device_model"] = self._model_from_serial(serial)

        if len(payload) >= 18:
            # M+21: bits0-6 SoC, bit7 dormancy.  The u0/p0 families reuse the
            # same byte as deviceAddFlag (bit7) + deviceAddStateCode (bits0-6).
            status = payload[17]
            soc = status & 0x7F
            if soc <= 100:
                metadata["state_of_charge_pct"] = soc
            dormant = bool(status & 0x80)
            metadata["dormant"] = dormant
            metadata["active"] = not dormant
            metadata["device_add_flag"] = dormant
            metadata["device_add_state_code"] = soc

        if len(payload) >= 19:
            # M+22: model byte; el/i.java also reads OTA bits out of it.
            model_byte = payload[18]
            metadata["product_type"] = model_byte
            metadata["upgrade_status"] = (model_byte >> 6) & 0x03
            metadata["config_state"] = model_byte & 0x3F

        if len(payload) >= 20:
            # M+23: bit2 charging; (x & 3) == 1 means sleeping.
            charge_byte = payload[19]
            metadata["charging"] = bool(charge_byte & 0x04)
            metadata["sleeping"] = (charge_byte & 0x03) == 1

        if len(payload) >= 21:
            metadata["config_state_v1"] = payload[20]

        if len(payload) >= 23:
            caps = payload[22]
            metadata["encrypted"] = bool(caps & 0x01)
            metadata["supports_verification"] = bool(caps & 0x02)
            metadata["verified"] = bool(caps & 0x04)
            metadata["encryption_type"] = (caps & 0x38) >> 3
            metadata["supports_5ghz"] = bool(caps & 0x40)
            metadata["ssl_type"] = (caps >> 7) & 0x01

        # The serial is broadcast in the clear and outlives MAC randomization,
        # so it is the better identity anchor (report "Privacy implications").
        if serial:
            id_hash = hashlib.sha256(f"ecoflow:{serial}".encode()).hexdigest()[:16]
        else:
            id_hash = self._mac_hash(raw)

        return ParseResult(
            parser_name="ecoflow",
            beacon_type="ecoflow",
            device_class="power",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex(),
            metadata=metadata,
        )

    @staticmethod
    def _mac_hash(raw) -> str:
        return hashlib.sha256(f"{raw.mac_address}:ecoflow".encode()).hexdigest()[:16]

    def _model_from_serial(self, serial):
        for prefix, model in SERIAL_PREFIX_MAP.items():
            if serial.startswith(prefix):
                return model
        return "Unknown EcoFlow"
