"""Tests for Allegion Engage commercial-lock plugin."""

import hashlib

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.allegion_engage import (
    AllegionEngageParser,
    ALLEGION_CID,
)


def _make_ad(**kw):
    defaults = {"timestamp": "2025-01-01T00:00:00Z", "mac_address": "AA:BB:CC:DD:EE:FF",
                "address_type": "random", "manufacturer_data": None, "service_data": None}
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _allegion_mfr(adv_version=1, device_type=0x0001, state=0x02, security_ver=1):
    """Build a v1-style Allegion mfr-data record.

    Layout (post-CID): adv_version + device_type_BE(2) + state + security_ver."""
    cid = (ALLEGION_CID).to_bytes(2, "little")  # 3B 01 little-endian
    payload = bytes([adv_version,
                     (device_type >> 8) & 0xFF,
                     device_type & 0xFF,
                     state,
                     security_ver])
    return cid + payload


def _allegion_v3_mfr(adv_version=3, device_type=0x0011, blocks=()):
    """Build a v3+ Allegion mfr-data record with LTV blocks."""
    cid = (ALLEGION_CID).to_bytes(2, "little")
    header = bytes([adv_version,
                    (device_type >> 8) & 0xFF,
                    device_type & 0xFF,
                    0x00])  # reserved
    block_bytes = b""
    for length, btype, value in blocks:
        block_bytes += bytes([length, btype]) + value
    block_bytes += b"\x00"  # end-of-stream
    return cid + header + block_bytes


def _register(registry):
    @register_parser(name="allegion_engage", company_id=ALLEGION_CID,
                     description="Allegion", version="1.0.0", core=False,
                     registry=registry)
    class _P(AllegionEngageParser):
        pass
    return _P


class TestAllegionMatching:
    def test_match_cid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=_allegion_mfr())
        assert len(registry.match(ad)) == 1


class TestAllegionV1Parsing:
    def test_adv_version(self):
        ad = _make_ad(manufacturer_data=_allegion_mfr(adv_version=1))
        result = AllegionEngageParser().parse(ad)
        assert result is not None
        assert result.metadata["adv_version"] == 1

    def test_device_type_decoded(self):
        ad = _make_ad(manufacturer_data=_allegion_mfr(device_type=0x0042))
        result = AllegionEngageParser().parse(ad)
        assert result.metadata["device_type"] == 0x0042

    def test_state_fdr(self):
        ad = _make_ad(manufacturer_data=_allegion_mfr(state=0x01))
        result = AllegionEngageParser().parse(ad)
        assert result.metadata["state"] == "factory_default"

    def test_state_commissioned(self):
        ad = _make_ad(manufacturer_data=_allegion_mfr(state=0x02))
        result = AllegionEngageParser().parse(ad)
        assert result.metadata["state"] == "commissioned"

    def test_state_unconnected(self):
        ad = _make_ad(manufacturer_data=_allegion_mfr(state=0x03))
        result = AllegionEngageParser().parse(ad)
        assert result.metadata["state"] == "unconnected"

    def test_security_version_v1(self):
        ad = _make_ad(manufacturer_data=_allegion_mfr(security_ver=2))
        result = AllegionEngageParser().parse(ad)
        assert result.metadata["security_version"] == 2


class TestAllegionV3Parsing:
    def test_adv_version_3(self):
        ad = _make_ad(manufacturer_data=_allegion_v3_mfr(adv_version=3))
        result = AllegionEngageParser().parse(ad)
        assert result.metadata["adv_version"] == 3

    def test_engage_block_decoded(self):
        # ENGAGE block (type 1): state + security_byte + payload
        engage_value = bytes([0x02, 0x01, 0xAA])
        ad = _make_ad(manufacturer_data=_allegion_v3_mfr(blocks=[
            (len(engage_value), 0x01, engage_value),
        ]))
        result = AllegionEngageParser().parse(ad)
        types = [b["type_name"] for b in result.metadata["protocol_blocks"]]
        assert "ENGAGE" in types

    def test_sapphire_block_decoded(self):
        sapphire_value = bytes([0x02, 0x03, 0x55])
        ad = _make_ad(manufacturer_data=_allegion_v3_mfr(blocks=[
            (len(sapphire_value), 0x03, sapphire_value),
        ]))
        result = AllegionEngageParser().parse(ad)
        types = [b["type_name"] for b in result.metadata["protocol_blocks"]]
        assert "SAPPHIRE" in types

    def test_multi_block_inventory(self):
        engage_value = bytes([0x02, 0x01])
        sapphire_value = bytes([0x02, 0x03])
        ad = _make_ad(manufacturer_data=_allegion_v3_mfr(blocks=[
            (len(engage_value), 0x01, engage_value),
            (len(sapphire_value), 0x03, sapphire_value),
        ]))
        result = AllegionEngageParser().parse(ad)
        assert len(result.metadata["protocol_blocks"]) == 2


class TestAllegionBasics:
    def test_basics(self):
        ad = _make_ad(manufacturer_data=_allegion_mfr())
        result = AllegionEngageParser().parse(ad)
        assert result.parser_name == "allegion_engage"
        assert result.beacon_type == "allegion_engage"
        assert result.device_class == "lock"

    def test_returns_none_short_payload(self):
        # Shorter than the v1 minimum (5 bytes post-CID) — should still match
        # by CID but with limited metadata.
        cid = (ALLEGION_CID).to_bytes(2, "little")
        ad = _make_ad(manufacturer_data=cid + b"\x01")
        result = AllegionEngageParser().parse(ad)
        assert result is not None
        # adv_version was the only byte we could read.
        assert result.metadata["adv_version"] == 1

    def test_returns_none_unrelated(self):
        # Wrong CID
        ad = _make_ad(manufacturer_data=b"\xFF\xFF\x01\x02\x03")
        assert AllegionEngageParser().parse(ad) is None
