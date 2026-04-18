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
