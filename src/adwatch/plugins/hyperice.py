"""Hyperice recovery devices (Hypervolt / Normatec / Venom / Hyperice X).

Per apk-ble-hunting/reports/hyperice-app_passive.md.

Normal mode: manufacturer data under company ID 0x08BA (2234, Hyperice).
The app fetches it with ``SparseArray.get(2234)`` which already strips the
company ID, so ``manufacturer_payload[0]`` = model number and
``manufacturer_payload[7]`` = submodel (Normatec 3 only). Identity only — no
telemetry in the advert.

DFU mode: Nordic company ID 0x0059 plus one of 25 exact DFU names. Nordic's
CID is never registered (it would claim every nRF device); the exact-name
allow-list is the match. Bare ``DfuTarg`` is the Nordic SDK default
bootloader name and is excluded from matching to avoid over-claiming.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser


HYPERICE_COMPANY_ID = 0x08BA
NORDIC_COMPANY_ID = 0x0059

MODEL_NUMBERS = {
    1: "Hypervolt",
    2: "Hypervolt Plus",
    3: "Vyper Go",
    4: "Vyper 3",
    5: "Hypervolt 2",
    6: "Hypervolt 2 Pro",
    7: "Normatec 2",
    8: "Normatec 2 Pro",
    9: "Normatec 3",
    10: "Hyperice X Knee",
    11: "Normatec Go",
    13: "Venom 2",
    14: "Venom Go",
    17: "Hyperice X Shoulder",
    18: "Normatec Elite",
    19: "Normatec Lower Leg",
    20: "Normatec 3 (China/Japan)",
    22: "NikeOmni",
    23: "Normatec Lower Leg (CN/JP)",
    24: "Normatec Premier (CN/JP)",
    25: "Normatec Premier EU",
    26: "Hyperice X 2",
    28: "Hyperboot (CN/JP)",
    30: "Hypervolt 3",
    31: "Hypervolt 3 Pro",
    32: "Normatec Elite Hip",
    34: "Normatec Premier Hip",
    35: "Hyperice X 2 (secondary)",
}

NORMATEC3_MODELS = frozenset({9, 20})
SUBMODELS = {0: "RYDER", 1: "MINEW"}

# Exact DFU-mode device names (ra3.java:1011-1013) -> family.
DFU_NAMES = {
    "HypervoltDFU": "Hypervolt",
    "Vyper 3.0 DFU": "Vyper",
    "Vyper 3 DFU": "Vyper",
    "Vyper Go DFU": "Vyper",
    "Hypervolt 2.0 DFU": "Hypervolt",
    "Hypervolt 2 DFU": "Hypervolt",
    "Hypervolt 2 Pro DFU": "Hypervolt",
    "Hypervolt 2.0 Pro DFU": "Hypervolt",
    "NT3_DFU_TARGET": "Normatec",
    "Normatec_DFU_TARGET": "Normatec",
    "NTGO_DFU_TARGET": "Normatec",
    "NT LL DFU": "Normatec",
    "HypericeXDfuTarg": "Hyperice X",
    "Hyperice X DFU": "Hyperice X",
    "VenomGoDfuTarg": "Venom",
    "Venom2DfuTarg": "Venom",
    "DfuTarg": "generic",
    "OMNIDfuTarg": "NikeOmni",
    "Hyperboot 2.4 DFU": "Hyperboot",
    "HX2 DFU": "Hyperice X",
    "NT Elite Hip DFU": "Normatec",
    "NT Elite DFU": "Normatec",
    "NT Premier Hip DFU": "Normatec",
    "NT Premier DFU": "Normatec",
    "HX2 DfuTarg": "Hyperice X",
}

# Nordic SDK default; shared by countless non-Hyperice nRF bootloaders.
_GENERIC_DFU_NAMES = frozenset({"DfuTarg"})
_MATCHABLE_DFU_NAMES = {n: f for n, f in DFU_NAMES.items() if n not in _GENERIC_DFU_NAMES}

DFU_NAME_PATTERN = "^(" + "|".join(
    re.escape(n) for n in sorted(_MATCHABLE_DFU_NAMES, key=len, reverse=True)
) + ")$"


@register_parser(
    name="hyperice",
    company_id=HYPERICE_COMPANY_ID,
    local_name_pattern=DFU_NAME_PATTERN,
    description="Hyperice recovery devices (Hypervolt / Normatec / Venom / Hyperice X)",
    version="1.0.0",
    core=False,
)
class HypericeParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        name = raw.local_name or ""
        cid = raw.company_id
        dfu_family = _MATCHABLE_DFU_NAMES.get(name)

        if cid != HYPERICE_COMPANY_ID and dfu_family is None:
            return None

        metadata: dict = {"dfu_mode": dfu_family is not None}
        payload = raw.manufacturer_payload if cid == HYPERICE_COMPANY_ID else None
        model_number = None

        if dfu_family is not None:
            metadata["dfu_name"] = name
            metadata["dfu_family"] = dfu_family
            if cid is not None:
                metadata["dfu_company_id"] = cid

        if payload:
            model_number = payload[0]
            model = MODEL_NUMBERS.get(model_number, f"unknown_{model_number}")
            lname = name.lower()
            if model_number == 1 and ("hypervolt+" in lname or "hypervolt plus" in lname):
                model = "Hypervolt Plus"
            if "Premier Hip" in name:
                model = "Normatec Premier Hip"
            metadata["model_number"] = model_number
            metadata["model"] = model
            if model_number in NORMATEC3_MODELS and len(payload) >= 8:
                sub = payload[7]
                metadata["submodel_code"] = sub
                metadata["submodel"] = SUBMODELS.get(sub, f"unknown_{sub}")

        basis = f"hyperice:{raw.mac_address}:{model_number if model_number is not None else dfu_family}"
        id_hash = hashlib.sha256(basis.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="hyperice",
            beacon_type="hyperice",
            device_class="recovery",
            identifier_hash=id_hash,
            raw_payload_hex=payload.hex() if payload else "",
            metadata=metadata,
        )

    def storage_schema(self):
        return None
