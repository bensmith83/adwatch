"""Tests for Toyota PAAK (Denso DKLib) phone-key plugin.

Layouts per apk-ble-hunting/reports/toyota-oneapp_passive.md.
"""

import hashlib
import struct

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.toyota_paak import (
    ToyotaPaakParser,
    TOYOTA_DENSO_UUID,
    TOYOTA_DENSO_UUID_HEX,
    APPLE_COMPANY_ID,
    STEADY_STATE_NAME,
)


def _make_ad(**kwargs):
    defaults = {
        "timestamp": "2026-08-16T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "random",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _ibeacon(uuid_hex: str, major: int, minor: int, tx: int = -59) -> bytes:
    return (
        struct.pack("<H", APPLE_COMPANY_ID)
        + bytes([0x02, 0x15])
        + bytes.fromhex(uuid_hex)
        + struct.pack(">HH", major, minor)
        + struct.pack("b", tx)
    )


def _register(registry):
    @register_parser(
        name="toyota_paak",
        company_id=APPLE_COMPANY_ID,
        service_uuid=TOYOTA_DENSO_UUID,
        description="Toyota PAAK",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(ToyotaPaakParser):
        pass

    return registry


class TestMatching:
    def test_matches_denso_service_uuid(self):
        reg = _register(ParserRegistry())
        ad = _make_ad(service_uuids=[TOYOTA_DENSO_UUID], local_name="Passive")
        assert len(reg.match(ad)) == 1

    def test_matches_uppercase_service_uuid(self):
        reg = _register(ParserRegistry())
        ad = _make_ad(service_uuids=[TOYOTA_DENSO_UUID.upper()])
        assert len(reg.match(ad)) == 1

    def test_matches_ibeacon_manufacturer_data(self):
        reg = _register(ParserRegistry())
        ad = _make_ad(manufacturer_data=_ibeacon(TOYOTA_DENSO_UUID_HEX, 7, 42))
        assert len(reg.match(ad)) == 1


class TestIBeaconPath:
    def test_decodes_major_minor_and_tx(self):
        p = ToyotaPaakParser()
        ad = _make_ad(manufacturer_data=_ibeacon(TOYOTA_DENSO_UUID_HEX, 0x1234, 0x00AB, -62))
        r = p.parse(ad)
        assert r is not None
        assert r.parser_name == "toyota_paak"
        assert r.device_class == "vehicle"
        assert r.metadata["major"] == 0x1234
        assert r.metadata["minor"] == 0x00AB
        assert r.metadata["tx_power"] == -62
        assert r.metadata["advert_role"] == "ibeacon_wake"
        assert r.metadata["key_fingerprint"] == "123400ab"

    def test_identity_from_major_minor_not_mac(self):
        p = ToyotaPaakParser()
        a = _make_ad(mac_address="11:22:33:44:55:66",
                     manufacturer_data=_ibeacon(TOYOTA_DENSO_UUID_HEX, 5, 9))
        b = _make_ad(mac_address="99:88:77:66:55:44",
                     manufacturer_data=_ibeacon(TOYOTA_DENSO_UUID_HEX, 5, 9))
        ra, rb = p.parse(a), p.parse(b)
        assert ra.identifier_hash == rb.identifier_hash
        expected = hashlib.sha256(b"toyota_paak:00050009").hexdigest()[:16]
        assert ra.identifier_hash == expected

    def test_different_key_different_identity(self):
        p = ToyotaPaakParser()
        a = _make_ad(manufacturer_data=_ibeacon(TOYOTA_DENSO_UUID_HEX, 5, 9))
        b = _make_ad(manufacturer_data=_ibeacon(TOYOTA_DENSO_UUID_HEX, 5, 10))
        assert p.parse(a).identifier_hash != p.parse(b).identifier_hash

    def test_rejects_other_proximity_uuid(self):
        p = ToyotaPaakParser()
        ad = _make_ad(manufacturer_data=_ibeacon("e20a39f473f54bc4186417d1ad07a962", 1, 2))
        assert p.parse(ad) is None

    def test_rejects_non_apple_cid(self):
        p = ToyotaPaakParser()
        data = bytearray(_ibeacon(TOYOTA_DENSO_UUID_HEX, 1, 2))
        data[0:2] = struct.pack("<H", 0x0075)
        assert p.parse(bytes(data) and _make_ad(manufacturer_data=bytes(data))) is None

    def test_rejects_truncated_ibeacon(self):
        p = ToyotaPaakParser()
        ad = _make_ad(manufacturer_data=_ibeacon(TOYOTA_DENSO_UUID_HEX, 1, 2)[:12])
        assert p.parse(ad) is None


class TestPeripheralPath:
    def test_service_uuid_only_advert(self):
        p = ToyotaPaakParser()
        ad = _make_ad(service_uuids=[TOYOTA_DENSO_UUID], local_name=STEADY_STATE_NAME)
        r = p.parse(ad)
        assert r is not None
        assert r.metadata["advert_role"] == "connectable_peripheral"
        assert r.metadata["device_name"] == STEADY_STATE_NAME
        assert r.metadata["name_state"] == "steady_state"
        assert "major" not in r.metadata

    def test_registration_mode_name_is_vehicle_id_fragment(self):
        p = ToyotaPaakParser()
        ad = _make_ad(service_uuids=[TOYOTA_DENSO_UUID], local_name="a1b2c3d4")
        r = p.parse(ad)
        assert r.metadata["name_state"] == "registration"
        assert r.metadata["vehicle_id_fragment"] == "a1b2c3d4"
        expected = hashlib.sha256(b"toyota_paak:vid:a1b2c3d4").hexdigest()[:16]
        assert r.identifier_hash == expected

    def test_falls_back_to_mac_identity(self):
        p = ToyotaPaakParser()
        ad = _make_ad(service_uuids=[TOYOTA_DENSO_UUID], mac_address="AA:BB:CC:DD:EE:FF")
        r = p.parse(ad)
        expected = hashlib.sha256(b"toyota_paak:AA:BB:CC:DD:EE:FF").hexdigest()[:16]
        assert r.identifier_hash == expected

    def test_unrelated_advert_returns_none(self):
        p = ToyotaPaakParser()
        ad = _make_ad(service_uuids=["fd6f"], local_name="Pixel 8")
        assert p.parse(ad) is None
