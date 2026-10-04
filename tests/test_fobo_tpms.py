"""Tests for FOBO Tire / FOBO Bike TPMS plugin (Salutica Allied).

Byte layouts per apk-ble-hunting/reports/salutica-fobotpms_passive.md.

The app slices the raw ScanRecord by absolute offset. Scan record layout:
  [0-2] flags AD, [3-6] 16-bit service-class AD (UUID LE at bytes 5-6),
  [7] len, [8] AD type, [9-10] CID / service UUID, [11..] payload.
The app's own FOBO-Link decoder does ``slice = result[11:]`` which confirms
the telemetry AD element's post-header payload starts at raw byte 11. So
raw byte N == manufacturer_payload[N - 11] (or service-data value[N - 11]).
"""

import hashlib
import struct

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.fobo_tpms import (
    FoboTpmsParser,
    FOBO_SERVICE_UUIDS,
    FOBO_FAMILIES,
    FOBO_OUI,
    FOBO_GATEWAY_NAME,
    SALUTICA_COMPANY_ID,
    decode_format_a,
    decode_format_b,
    decode_format_d,
)


FOBO_MAC = "00:15:88:12:34:56"
OTHER_MAC = "C0:11:22:33:44:55"


def _uuid(short: str) -> str:
    return f"0000{short}-0000-1000-8000-00805f9b34fb"


def _make_ad(**kwargs):
    defaults = {
        "timestamp": "2026-10-01T00:00:00Z",
        "mac_address": FOBO_MAC,
        "address_type": "public",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


def _mfr(seg: bytes, cid: int = 0x0127) -> bytes:
    """seg[k] == raw scan-record byte 11 + k."""
    return struct.pack("<H", cid) + seg


def _register(registry):
    @register_parser(
        name="fobo_tpms",
        company_id=SALUTICA_COMPANY_ID,
        service_uuid=list(FOBO_SERVICE_UUIDS),
        local_name_pattern=r"^FOBO-GATEWAY$",
        description="FOBO",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(FoboTpmsParser):
        pass

    return _P


# Format A: raw bytes 17..20 -> seg[6..9]
# byte17 = flags (hi nibble 3), byte18 = 75 (-> 25 C), W = (33<<10)|500
W_A = (33 << 10) | 500
SEG_A = bytes(6) + bytes([0x30, 75]) + struct.pack(">H", W_A)

# Format B words: temp 25 C, battery 3000 mV, rotation flag (word1 bit14) set
W1_B = 0x4000 | (100 << 7) | 65
W2_B = 800
SEG_B = bytes(6) + struct.pack(">HH", W1_B, W2_B)


class TestConstants:
    def test_uuids(self):
        for short in ("ee00", "eefe", "faf0", "0126", "0129", "012b", "fcf0", "014a", "010a"):
            assert _uuid(short) in FOBO_SERVICE_UUIDS

    def test_families(self):
        assert FOBO_FAMILIES["ee00"][0] == "tire"
        assert FOBO_FAMILIES["eefe"][0] == "bike"
        assert FOBO_FAMILIES["faf0"][0] == "midget"
        assert FOBO_FAMILIES["014a"][0] == "fobo_link"
        assert FOBO_FAMILIES["010a"][0] == "gateway"

    def test_company_id(self):
        assert SALUTICA_COMPANY_ID == 0x0127

    def test_oui_and_name(self):
        assert FOBO_OUI == "00:15:88"
        assert FOBO_GATEWAY_NAME == "FOBO-GATEWAY"


class TestDecoders:
    def test_format_a(self):
        d = decode_format_a(0x30, 75, W_A)
        assert d["temperature_c"] == 25
        assert d["pressure_raw"] == 500
        assert d["battery_mv"] == 3300
        assert d["flags_nibble"] == 3

    def test_format_a_pressure_clamp(self):
        d = decode_format_a(0x00, 50, (30 << 10) | 30)
        assert d["pressure_raw"] == 0
        assert d["pressure_deflated"] is True
        assert d["temperature_c"] == 0
        assert d["battery_mv"] == 3000

    def test_format_b(self):
        d = decode_format_b(W1_B, W2_B)
        assert d["temperature_c"] == 25
        assert d["battery_mv"] == 3000
        assert d["pressure_raw"] == 800
        assert d["rotating"] is True

    def test_format_b_link_rotation_bit(self):
        d = decode_format_b((100 << 7) | 65, 0x8000 | 800, rotation_in_word2=True)
        assert d["rotating"] is True
        assert d["pressure_raw"] == 800
        d2 = decode_format_b(0x4000 | (100 << 7) | 65, 800, rotation_in_word2=True)
        assert d2["rotating"] is False

    def test_format_b_temp_range(self):
        assert decode_format_b(0x0000, 100)["temperature_c"] == -40
        assert decode_format_b(0x007F, 100)["temperature_c"] == 87
        assert decode_format_b(0x3F80, 100)["battery_mv"] == 3270

    def test_format_d_tire_1_4(self):
        major = (2 << 8) | 75   # tireId 2, temp 25
        minor = (31 << 10) | 400
        d = decode_format_d(major, minor)
        assert d["tire_id"] == 2
        assert d["position"] == 2
        assert d["temperature_c"] == 25
        assert d["pressure_raw"] == 400
        assert d["battery_mv"] == 3100

    def test_format_d_tire_5_8(self):
        major = (6 << 8) | 60   # tireId 6 -> position 2, temp 10
        minor = (25 << 11) | 1500
        d = decode_format_d(major, minor)
        assert d["tire_id"] == 6
        assert d["position"] == 2
        assert d["temperature_c"] == 10
        assert d["pressure_raw"] == 1500
        assert d["battery_mv"] == 25 * 40 + 2000

    def test_format_d_display_battery(self):
        d = decode_format_d(0x0000, (29 << 10))
        assert d["tire_id"] == 0
        assert d["display_battery_mv"] == 2900
        assert "pressure_raw" not in d

    def test_format_d_no_reading(self):
        d = decode_format_d((1 << 8) | 75, 0xFFFF)
        assert d["no_reading"] is True
        assert d["pressure_raw"] == 0
        assert d["battery_mv"] == 0


class TestMatching:
    @pytest.mark.parametrize("short", ["ee00", "eefe", "faf0", "fcf0", "014a", "010a"])
    def test_uuid_match(self, short):
        reg = ParserRegistry()
        _register(reg)
        assert len(reg.match(_make_ad(service_uuids=[_uuid(short)]))) == 1

    def test_name_match(self):
        reg = ParserRegistry()
        _register(reg)
        assert len(reg.match(_make_ad(local_name="FOBO-GATEWAY"))) == 1

    def test_cid_match(self):
        reg = ParserRegistry()
        _register(reg)
        assert len(reg.match(_make_ad(manufacturer_data=_mfr(SEG_A)))) == 1

    def test_no_match_unrelated(self):
        reg = ParserRegistry()
        _register(reg)
        assert reg.match(_make_ad(service_uuids=[_uuid("180f")], local_name="Foo")) == []


class TestClassicFormatA:
    @pytest.mark.parametrize("short,family", [("ee00", "tire"), ("eefe", "bike")])
    def test_decode(self, short, family):
        ad = _make_ad(service_uuids=[_uuid(short)], manufacturer_data=_mfr(SEG_A))
        r = FoboTpmsParser().parse(ad)
        assert r is not None
        assert r.parser_name == "fobo_tpms"
        assert r.device_class == "sensor"
        m = r.metadata
        assert m["family"] == family
        assert m["wire_format"] == "A"
        assert m["temperature_c"] == 25
        assert m["pressure_raw"] == 500
        assert m["battery_mv"] == 3300
        assert m["flags_nibble"] == 3
        assert m["oui_match"] is True
        assert m["sensor_id"] == "001588123456"

    def test_identity_is_sensor_id(self):
        ad = _make_ad(service_uuids=[_uuid("ee00")], manufacturer_data=_mfr(SEG_A))
        r = FoboTpmsParser().parse(ad)
        assert r.identifier_hash == hashlib.sha256(b"fobo:001588123456").hexdigest()[:16]

    def test_service_data_carrier(self):
        """Telemetry element may be service data rather than mfr data."""
        ad = _make_ad(service_uuids=[_uuid("eefe")],
                      service_data={"eefe": SEG_A})
        r = FoboTpmsParser().parse(ad)
        assert r.metadata["temperature_c"] == 25
        assert r.metadata["pressure_raw"] == 500

    def test_short_payload_identity_only(self):
        ad = _make_ad(service_uuids=[_uuid("ee00")], manufacturer_data=_mfr(b"\x01\x02"))
        r = FoboTpmsParser().parse(ad)
        assert r is not None
        assert "temperature_c" not in r.metadata
        assert r.metadata["family"] == "tire"


class TestNewFormatB:
    @pytest.mark.parametrize("short,family", [
        ("faf0", "midget"), ("0126", "new_midget"), ("0129", "elite"), ("012b", "next"),
    ])
    def test_decode(self, short, family):
        ad = _make_ad(service_uuids=[_uuid(short)], manufacturer_data=_mfr(SEG_B))
        r = FoboTpmsParser().parse(ad)
        m = r.metadata
        assert m["family"] == family
        assert m["wire_format"] == "B"
        assert m["temperature_c"] == 25
        assert m["battery_mv"] == 3000
        assert m["pressure_raw"] == 800
        assert m["rotating"] is True

    def test_next_beacon_words_at_25(self):
        # raw bytes 25-28 -> seg[14..17]
        seg = bytes(14) + struct.pack(">HH", W1_B, W2_B)
        ad = _make_ad(service_uuids=[_uuid("fcf0")], manufacturer_data=_mfr(seg))
        m = FoboTpmsParser().parse(ad).metadata
        assert m["family"] == "next_beacon"
        assert m["temperature_c"] == 25
        assert m["pressure_raw"] == 800


class TestLinkFormatC:
    def _seg(self, two=True):
        s1 = bytes(4) + bytes.fromhex("aabbcc") + struct.pack(">HH", (100 << 7) | 65, 0x8000 | 800)
        if not two:
            return s1
        return s1 + bytes.fromhex("ddeeff") + struct.pack(">HH", (50 << 7) | 50, 300)

    def test_two_sensors(self):
        ad = _make_ad(service_uuids=[_uuid("014a")], manufacturer_data=_mfr(self._seg()))
        r = FoboTpmsParser().parse(ad)
        m = r.metadata
        assert m["family"] == "fobo_link"
        assert m["wire_format"] == "C"
        assert m["relay_sensor_count"] == 2
        assert m["sensor1_id"] == "001588aabbcc"
        assert m["sensor1_temperature_c"] == 25
        assert m["sensor1_battery_mv"] == 3000
        assert m["sensor1_pressure_raw"] == 800
        assert m["sensor1_rotating"] is True
        assert m["sensor2_id"] == "001588ddeeff"
        assert m["sensor2_temperature_c"] == 10
        assert m["sensor2_battery_mv"] == 2500
        assert m["sensor2_pressure_raw"] == 300
        assert m["sensor2_rotating"] is False

    def test_one_sensor(self):
        ad = _make_ad(service_uuids=[_uuid("014a")], manufacturer_data=_mfr(self._seg(two=False)))
        m = FoboTpmsParser().parse(ad).metadata
        assert m["relay_sensor_count"] == 1
        assert "sensor2_id" not in m

    def test_link_without_oui_but_shape_ok_claims(self):
        ad = _make_ad(mac_address=OTHER_MAC, service_uuids=[_uuid("014a")],
                      manufacturer_data=_mfr(self._seg(), cid=0x0D00))
        r = FoboTpmsParser().parse(ad)
        assert r is not None
        assert r.metadata["oui_match"] is False

    def test_link_bare_uuid_no_oui_rejected(self):
        """0x014A is a generic-looking 16-bit UUID: need shape or OUI."""
        ad = _make_ad(mac_address=OTHER_MAC, service_uuids=[_uuid("014a")])
        assert FoboTpmsParser().parse(ad) is None

    def test_link_short_payload_no_oui_rejected(self):
        ad = _make_ad(mac_address=OTHER_MAC, service_uuids=[_uuid("014a")],
                      manufacturer_data=_mfr(b"\x01\x02\x03", cid=0x0D00))
        assert FoboTpmsParser().parse(ad) is None


class TestGatewayFormatD:
    def test_gateway_decode(self):
        major = (2 << 8) | 75
        minor = (31 << 10) | 400
        seg = bytes(14) + struct.pack(">HH", major, minor)
        ad = _make_ad(service_uuids=[_uuid("010a")], manufacturer_data=_mfr(seg))
        m = FoboTpmsParser().parse(ad).metadata
        assert m["family"] == "gateway"
        assert m["wire_format"] == "D"
        assert m["tire_id"] == 2
        assert m["temperature_c"] == 25
        assert m["pressure_raw"] == 400
        assert m["battery_mv"] == 3100

    def test_gateway_ibeacon_frame(self):
        """Apple iBeacon carrier: major/minor at mfr_data[20:24] (raw 25-28)."""
        major = (6 << 8) | 60
        minor = (25 << 11) | 1500
        mfr = b"\x4c\x00\x02\x15" + bytes(16) + struct.pack(">HH", major, minor) + b"\xc5"
        ad = _make_ad(service_uuids=[_uuid("010a")], manufacturer_data=mfr)
        m = FoboTpmsParser().parse(ad).metadata
        assert m["tire_id"] == 6
        assert m["position"] == 2
        assert m["pressure_raw"] == 1500

    def test_gateway_bare_uuid_no_oui_rejected(self):
        ad = _make_ad(mac_address=OTHER_MAC, service_uuids=[_uuid("010a")])
        assert FoboTpmsParser().parse(ad) is None

    def test_gateway_name_only(self):
        ad = _make_ad(mac_address=OTHER_MAC, local_name="FOBO-GATEWAY")
        r = FoboTpmsParser().parse(ad)
        assert r is not None
        assert r.metadata["family"] == "gateway"
        assert r.device_class == "gateway"


class TestGenericGating:
    @pytest.mark.parametrize("short", ["0126", "0129", "012b"])
    def test_weak_uuid_bare_no_oui_rejected(self, short):
        ad = _make_ad(mac_address=OTHER_MAC, service_uuids=[_uuid(short)])
        assert FoboTpmsParser().parse(ad) is None

    def test_weak_uuid_with_oui_identity_only(self):
        ad = _make_ad(service_uuids=[_uuid("0129")])
        r = FoboTpmsParser().parse(ad)
        assert r is not None
        assert r.metadata["family"] == "elite"

    def test_salutica_cid_counts_as_corroboration(self):
        ad = _make_ad(mac_address=OTHER_MAC, service_uuids=[_uuid("0129")],
                      manufacturer_data=_mfr(b"\x00"))
        r = FoboTpmsParser().parse(ad)
        assert r is not None
        assert r.metadata["salutica_cid"] is True

    def test_salutica_cid_only(self):
        ad = _make_ad(mac_address=OTHER_MAC, manufacturer_data=_mfr(SEG_A))
        r = FoboTpmsParser().parse(ad)
        assert r is not None
        assert r.metadata["family"] == "unknown"

    def test_foreign_cid_short_payload_no_oui_rejected(self):
        ad = _make_ad(mac_address=OTHER_MAC, service_uuids=[_uuid("014a")],
                      manufacturer_data=_mfr(b"\x01\x02\x03", cid=0x0D00))
        assert FoboTpmsParser().parse(ad) is None

    def test_no_fobo_signal(self):
        ad = _make_ad(service_uuids=[_uuid("180f")])
        assert FoboTpmsParser().parse(ad) is None


class TestGenericTpmsStandsDown:
    def test_generic_tpms_ignores_fobo_uuid(self):
        from adwatch.plugins.tpms import TPMSParser
        ad = _make_ad(service_uuids=[_uuid("ee00")], manufacturer_data=_mfr(SEG_A, cid=0x0001))
        assert TPMSParser().parse(ad) is None

    def test_generic_tpms_ignores_fobo_oui(self):
        from adwatch.plugins.tpms import TPMSParser
        ad = _make_ad(manufacturer_data=_mfr(SEG_A, cid=0x0001))
        assert TPMSParser().parse(ad) is None

    def test_generic_tpms_still_parses_other(self):
        from adwatch.plugins.tpms import TPMSParser
        ad = _make_ad(mac_address=OTHER_MAC,
                      manufacturer_data=_mfr(bytes([1, 150, 65]) + struct.pack("<H", 25000), cid=0x0001))
        assert TPMSParser().parse(ad) is not None
