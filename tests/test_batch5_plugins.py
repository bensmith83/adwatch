"""Smoke tests for final-batch plugins.

Each plugin gets a minimal detection test + device_class check. Deeper byte
decoding tests omitted where the passive report itself notes the byte layout
isn't recoverable from the APK (FLIR, Fluke, Masimo, Milwaukee etc.).
"""

import struct

import pytest

from adwatch.models import RawAdvertisement


def _make_ad(**kwargs):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "random",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _mfr(company_id: int, payload: bytes = b"") -> bytes:
    return struct.pack("<H", company_id) + payload


def test_aiper_name_match():
    from adwatch.plugins.aiper import AiperParser
    result = AiperParser().parse(_make_ad(local_name="Aiper Seagull Pro"))
    assert result and result.device_class == "pool_cleaner"


def test_anova_uuid_match():
    from adwatch.plugins.anova import AnovaParser, ANOVA_UUID_NEURON
    result = AnovaParser().parse(_make_ad(service_uuids=[ANOVA_UUID_NEURON]))
    assert result and result.device_class == "appliance"


def test_ascensia_company_id():
    from adwatch.plugins.ascensia_contour import AscensiaContourParser
    result = AscensiaContourParser().parse(_make_ad(manufacturer_data=_mfr(0x0167, b"\x00")))
    assert result and result.device_class == "medical"


def test_ascensia_name():
    from adwatch.plugins.ascensia_contour import AscensiaContourParser
    result = AscensiaContourParser().parse(_make_ad(local_name="Contour Plus"))
    assert result is not None


def test_fi_collar_uuid():
    from adwatch.plugins.barkinglabs_fi import BarkingLabsFiParser, COLLAR_UUID
    result = BarkingLabsFiParser().parse(_make_ad(service_uuids=[COLLAR_UUID]))
    assert result and result.metadata["role"] == "collar"


def test_fi_base_proxy_role():
    from adwatch.plugins.barkinglabs_fi import BarkingLabsFiParser, BASE_PROXY_UUID
    result = BarkingLabsFiParser().parse(_make_ad(service_uuids=[BASE_PROXY_UUID]))
    assert result.metadata["role"] == "base_proxy"


def test_concept2_pm5_name():
    from adwatch.plugins.concept2_pm5 import Concept2PM5Parser
    result = Concept2PM5Parser().parse(_make_ad(local_name="PM5 12345"))
    assert result and result.device_class == "fitness_equipment"


def test_flir_company_id():
    from adwatch.plugins.flir_tools import FlirToolsParser
    result = FlirToolsParser().parse(_make_ad(manufacturer_data=_mfr(0x0AE9, b"\x01\x02")))
    assert result and result.metadata["product_family"] == "FLIR One thermal"


def test_fluke_uuid_base():
    from adwatch.plugins.fluke import FlukeParser
    result = FlukeParser().parse(_make_ad(
        service_uuids=["b6981234-7562-11e2-b50d-00163e46f8fe"]
    ))
    assert result
    assert result.metadata["instrument_family_code"] == "1234"


def test_insulet_omnipod_name():
    from adwatch.plugins.insulet_omnipod import InsuletOmnipodParser
    result = InsuletOmnipodParser().parse(_make_ad(local_name="Omnipod 5 PDM"))
    assert result and result.device_class == "medical"


def test_irobot_name():
    from adwatch.plugins.irobot import IRobotParser
    result = IRobotParser().parse(_make_ad(local_name="Roomba j7+"))
    assert result and result.device_class == "vacuum"


def test_irobot_magic_mfr_bytes():
    from adwatch.plugins.irobot import IRobotParser, _IROBOT_MFR_MAGIC_B3_B4
    # Bytes: [company_id LE][byte2 unknown][0x31][0x10]
    mfr = bytes([0xA8, 0x01, 0x00]) + bytes(_IROBOT_MFR_MAGIC_B3_B4)
    result = IRobotParser().parse(_make_ad(manufacturer_data=mfr))
    assert result and result.metadata["mfr_magic_match"] is True


def test_irobot_does_not_claim_raw_mammotion_company_id():
    # Mammotion also uses 0x01A8; iRobot only claims the ad if the magic
    # follows. Mammotion-shaped ad (no 0x31 0x10 at bytes 3-4) should NOT
    # match iRobot.
    from adwatch.plugins.irobot import IRobotParser
    mammotion_mfr = _mfr(0x01A8, bytes(12))  # no magic
    result = IRobotParser().parse(_make_ad(manufacturer_data=mammotion_mfr))
    assert result is None


def test_kinsa_name():
    from adwatch.plugins.kinsa import KinsaParser
    result = KinsaParser().parse(_make_ad(local_name="Kinsa QuickCare"))
    assert result and result.device_class == "medical"


def test_kinsa_service_uuid_base():
    from adwatch.plugins.kinsa import KinsaParser
    result = KinsaParser().parse(_make_ad(
        service_uuids=["00000000-1234-746c-6165-4861736e694b"]
    ))
    assert result is not None


def test_masimo_company_id():
    from adwatch.plugins.masimo import MasimoParser
    result = MasimoParser().parse(_make_ad(manufacturer_data=_mfr(0x0243, b"\x01\x02")))
    assert result and result.device_class == "medical"


def test_maytronics_name_serial():
    from adwatch.plugins.maytronics import MaytronicsParser
    result = MaytronicsParser().parse(_make_ad(local_name="ABC12345"))
    assert result
    assert result.metadata["serial_number"] == "ABC12345"


def test_maytronics_mfr_layout():
    from adwatch.plugins.maytronics import MaytronicsParser
    # [model=0x6C][proto=1][skip=0][serial_lo=0x12][serial_hi=0x34][mu_ver=5]
    payload = bytes([0x6C, 1, 0, 0x12, 0x34, 5])
    result = MaytronicsParser().parse(_make_ad(manufacturer_data=_mfr(0xABCD, payload)))
    assert result.metadata["model"] == "Dolphin M-series"
    assert result.metadata["protocol_version"] == 1
    assert result.metadata["serial_hash"] == 0x3412
    assert result.metadata["mu_version_byte"] == 5


def test_tapkey_service_uuid():
    from adwatch.plugins.tapkey import TapkeyParser, TAPKEY_SERVICE_UUID
    result = TapkeyParser().parse(_make_ad(service_uuids=[TAPKEY_SERVICE_UUID]))
    assert result and result.device_class == "lock"


def test_tapkey_magic_byte_complete():
    from adwatch.plugins.tapkey import TapkeyParser
    mfr = _mfr(0xABCD, bytes([0x01, 0xDE, 0xAD, 0xBE]))  # magic & 0x7F == 1, bit 7 clear
    result = TapkeyParser().parse(_make_ad(manufacturer_data=mfr))
    assert result.metadata["magic_match"] is True
    assert result.metadata["is_lock_id_incomplete"] is False
    assert result.metadata["lock_id_fragment_hex"] == "deadbe"


def test_tapkey_magic_byte_incomplete_flag():
    from adwatch.plugins.tapkey import TapkeyParser
    mfr = _mfr(0xABCD, bytes([0x81, 0xFE]))  # bit 7 set = incomplete
    result = TapkeyParser().parse(_make_ad(manufacturer_data=mfr))
    assert result.metadata["is_lock_id_incomplete"] is True


def test_volvo_ibeacon_match():
    from adwatch.plugins.volvo import VolvoParser, VOLVO_IBEACON_UUID
    # Apple iBeacon wrapper: [02][15][uuid(16)][major(2)BE][minor(2)BE][tx_power(1)]
    payload = bytes([0x02, 0x15]) + bytes.fromhex(VOLVO_IBEACON_UUID) \
            + bytes([0x12, 0x34, 0xAB, 0xCD, 0xC5])
    mfr = _mfr(0x004C, payload)
    result = VolvoParser().parse(_make_ad(manufacturer_data=mfr))
    assert result is not None
    assert result.metadata["volvo_proximity_match"] is True
    assert result.metadata["major"] == 0x1234
    assert result.metadata["minor"] == 0xABCD


def test_volvo_non_volvo_ibeacon_rejected():
    from adwatch.plugins.volvo import VolvoParser
    # Wrong proximity UUID → not Volvo.
    payload = bytes([0x02, 0x15]) + bytes(16) + bytes([0, 0, 0, 0, 0])
    mfr = _mfr(0x004C, payload)
    assert VolvoParser().parse(_make_ad(manufacturer_data=mfr)) is None


def test_volvo_name_alone_does_not_classify():
    # A device named "Volvo ..." without the iBeacon proximity UUID must not
    # classify as a Volvo vehicle — UUID is the primary signal.
    from adwatch.plugins.volvo import VolvoParser
    assert VolvoParser().parse(_make_ad(local_name="Volvo XC40")) is None


# ---- Owlet (baby HR/SpO2 monitor) -----------------------------------------

def test_owlet_company_id():
    from adwatch.plugins.owlet import OwletParser, OWLET_COMPANY_ID
    result = OwletParser().parse(_make_ad(manufacturer_data=_mfr(OWLET_COMPANY_ID, b"\x00\x00")))
    assert result and result.device_class == "medical"


def test_owlet_service_uuid():
    from adwatch.plugins.owlet import OwletParser, OWLET_SERVICE_UUID
    result = OwletParser().parse(_make_ad(service_uuids=[OWLET_SERVICE_UUID]))
    assert result is not None
    assert result.metadata["has_owlet_service"] is True


def test_owlet_name_ob_alone_does_not_classify():
    # "OB" is short and could collide with other devices; require UUID or CID.
    from adwatch.plugins.owlet import OwletParser
    assert OwletParser().parse(_make_ad(local_name="OB")) is None


def test_owlet_full_signature():
    from adwatch.plugins.owlet import OwletParser, OWLET_COMPANY_ID, OWLET_SERVICE_UUID
    result = OwletParser().parse(_make_ad(
        local_name="OB",
        manufacturer_data=_mfr(OWLET_COMPANY_ID, bytes([0x00, 0x00])),
        service_uuids=[OWLET_SERVICE_UUID],
    ))
    assert result.metadata["device_name"] == "OB"
    assert result.metadata["has_owlet_service"] is True


# ---- Trackonomy Systems (asset tracker) -----------------------------------

def test_trackonomy_company_id():
    from adwatch.plugins.trackonomy import TrackonomyParser, TRACKONOMY_COMPANY_ID
    payload = bytes.fromhex("4956e29f84211e44ffb51e")
    result = TrackonomyParser().parse(_make_ad(manufacturer_data=_mfr(TRACKONOMY_COMPANY_ID, payload)))
    assert result and result.device_class == "asset_tracker"
    assert result.metadata["company_id_hex"] == "0x0EF7"


def test_trackonomy_rejects_other_company_id():
    from adwatch.plugins.trackonomy import TrackonomyParser
    assert TrackonomyParser().parse(_make_ad(manufacturer_data=_mfr(0x004C, b"\x00"))) is None


# ---- iRobot: second service UUID (Robot Control) --------------------------

def test_irobot_alt_service_uuid():
    from adwatch.plugins.irobot import IRobotParser, IROBOT_ALT_SERVICE_UUID
    result = IRobotParser().parse(_make_ad(service_uuids=[IROBOT_ALT_SERVICE_UUID]))
    assert result and result.device_class == "vacuum"
    assert result.metadata["has_irobot_service"] is True


# ---- Tesla: non-vehicle product (CID 0x022B mfr-data) ---------------------

def test_tesla_company_id_non_vehicle():
    from adwatch.plugins.tesla import TeslaParser, TESLA_COMPANY_ID
    # Capture: 2B 02 01 FE 03 — CID 0x022B + 3-byte payload starting 01 FE 03.
    result = TeslaParser().parse(_make_ad(manufacturer_data=_mfr(TESLA_COMPANY_ID, bytes([0x01, 0xFE, 0x03]))))
    assert result and result.device_class == "tesla_product"
    assert result.metadata["product_kind"] == "non_vehicle"


def test_tesla_vehicle_via_service_uuid_still_works():
    # Existing path must not regress.
    from adwatch.plugins.tesla import TeslaParser, TESLA_SERVICE_UUID
    result = TeslaParser().parse(_make_ad(service_uuids=[TESLA_SERVICE_UUID]))
    assert result and result.device_class == "vehicle"


# ---- Cold-chain beacon (UUID 56D63956 — unidentified vendor) -------------

def test_cold_chain_56d6_extracts_sensor_id():
    from adwatch.plugins.cold_chain_56d6 import (
        ColdChain56d6Parser,
        COLD_CHAIN_56D6_UUID,
    )
    # 7-byte service-data: 0x00 + 6 ASCII chars (observed: "SSFYV3", "1ZNQGY", "LYHR3S")
    svc = {COLD_CHAIN_56D6_UUID: bytes([0x00]) + b"SSFYV3"}
    result = ColdChain56d6Parser().parse(_make_ad(service_data=svc))
    assert result and result.device_class == "sensor"
    assert result.metadata["sensor_id"] == "SSFYV3"


def test_cold_chain_56d6_identity_uses_sensor_id():
    # sensor_id appears stable per-device; identity should derive from it,
    # not from the (likely-rotating) MAC.
    import hashlib
    from adwatch.plugins.cold_chain_56d6 import (
        ColdChain56d6Parser,
        COLD_CHAIN_56D6_UUID,
    )
    svc = {COLD_CHAIN_56D6_UUID: bytes([0x00]) + b"1ZNQGY"}
    result = ColdChain56d6Parser().parse(_make_ad(service_data=svc))
    expected = hashlib.sha256(b"cold_chain_56d6:1ZNQGY").hexdigest()[:16]
    assert result.identifier_hash == expected


def test_cold_chain_56d6_rejects_other_uuid():
    from adwatch.plugins.cold_chain_56d6 import ColdChain56d6Parser
    svc = {"0000feed-0000-1000-8000-00805f9b34fb": bytes([0x00]) + b"ABCDEF"}
    assert ColdChain56d6Parser().parse(_make_ad(service_data=svc)) is None


def test_cold_chain_56d6_rejects_wrong_payload_shape():
    # Wrong leading byte or wrong length should fall through.
    from adwatch.plugins.cold_chain_56d6 import (
        ColdChain56d6Parser,
        COLD_CHAIN_56D6_UUID,
    )
    svc_bad_lead = {COLD_CHAIN_56D6_UUID: bytes([0xFF]) + b"SSFYV3"}
    assert ColdChain56d6Parser().parse(_make_ad(service_data=svc_bad_lead)) is None

    svc_short = {COLD_CHAIN_56D6_UUID: bytes([0x00, 0x41, 0x42])}
    assert ColdChain56d6Parser().parse(_make_ad(service_data=svc_short)) is None


# ---- Tuya: Smart.XX.WIFI pairing-mode clone --------------------------------

def test_tuya_clone_pairing_name_matches():
    from adwatch.plugins.tuya import TuyaParser
    # Cheap Tuya-clone WiFi smart-plug in pairing mode — name only, no
    # SIG-correct mfr-data.
    result = TuyaParser().parse(_make_ad(local_name="Smart.A5.WIFI"))
    assert result is not None
    assert result.device_class == "smart_home"
    assert result.metadata["match_source"] == "name_regex"
    assert result.metadata["pairing_mode_clone"] is True


def test_tuya_clone_pairing_name_rejects_wrong_shape():
    from adwatch.plugins.tuya import TuyaParser
    assert TuyaParser().parse(_make_ad(local_name="Smart.WIFI")) is None
    assert TuyaParser().parse(_make_ad(local_name="Smart.A5.WIFI.extra")) is None
    # Lowercase chars in the middle should not match (observed pattern is uppercase/digit).
    assert TuyaParser().parse(_make_ad(local_name="Smart.ab.WIFI")) is None


def test_tuya_cid_path_still_works():
    # Existing CID path must not regress.
    from adwatch.plugins.tuya import TuyaParser, TUYA_COMPANY_ID
    mfr = TUYA_COMPANY_ID.to_bytes(2, "little") + bytes([0x03, 0x01])
    result = TuyaParser().parse(_make_ad(manufacturer_data=mfr))
    assert result is not None
    assert result.metadata.get("match_source") != "name_regex"
    assert result.metadata["pairing"] is True
