"""Tests for Nothing earbuds / CMF plugin."""

import struct
import hashlib

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.nothing import (
    NothingParser, NOTHING_COMPANY_ID, NOTHING_COMPANY_ID_SENTINEL,
    FAST_PAIR_UUID, ALL_NOTHING_CIDS,
)


def _make_ad(**kw):
    defaults = {"timestamp": "2025-01-01T00:00:00Z", "mac_address": "AA:BB:CC:DD:EE:FF",
                "address_type": "random", "manufacturer_data": None, "service_data": None}
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(name="nothing", company_id=ALL_NOTHING_CIDS,
                     service_uuid=FAST_PAIR_UUID,
                     local_name_pattern=r"^(Nothing|CMF )",
                     description="Nothing", version="1.0.0", core=False, registry=registry)
    class _P(NothingParser):
        pass
    return _P


def _nothing_mfr(cid=NOTHING_COMPANY_ID, payload=b""):
    return struct.pack("<H", cid) + payload


class TestNothingMatching:
    def test_match_nothing_cid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=_nothing_mfr())
        assert len(registry.match(ad)) == 1

    def test_match_sentinel_cid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(manufacturer_data=_nothing_mfr(cid=NOTHING_COMPANY_ID_SENTINEL))
        assert len(registry.match(ad)) == 1

    def test_match_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="Nothing ear (2)")
        assert len(registry.match(ad)) == 1

    def test_match_cmf_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="CMF Buds Pro")
        assert len(registry.match(ad)) == 1


class TestNothingParsing:
    def test_persistent_id_from_last_6_bytes(self):
        # mfr CID + some prefix + 6 trailing ID bytes
        payload = b"\x00\x01\x02\xaa\xbb\xcc\xdd\xee\xff"  # last 6 = aabbccddeeff
        ad = _make_ad(manufacturer_data=_nothing_mfr(payload=payload))
        result = NothingParser().parse(ad)
        assert result.metadata["persistent_id_hex"] == "aabbccddeeff"

    def test_fast_pair_short_form(self):
        ad = _make_ad(
            local_name="Nothing ear (2)",
            service_data={"fe2c": b"\x12\x34\x56"},
        )
        result = NothingParser().parse(ad)
        assert result.metadata["fast_pair_present"] is True
        assert result.metadata["fast_pair_model_id"] == 0x123456
        assert result.metadata["fast_pair_mode"] == "discoverable"

    def test_fast_pair_account_key_filter(self):
        ad = _make_ad(
            local_name="Nothing ear (2)",
            service_data={"fe2c": b"\x00" * 16},
        )
        result = NothingParser().parse(ad)
        assert result.metadata["fast_pair_mode"] == "account_key_filter"

    def test_high_confidence_with_both_signals(self):
        ad = _make_ad(
            manufacturer_data=_nothing_mfr(payload=b"\xaa\xbb\xcc\xdd\xee\xff"),
            service_data={"fe2c": b"\x12\x34\x56"},
        )
        result = NothingParser().parse(ad)
        assert result.metadata["high_confidence"] is True

    def test_fast_pair_alone_does_not_match(self):
        # Per the gating, FP alone (without Nothing CID or name) shouldn't match.
        ad = _make_ad(service_data={"fe2c": b"\x12\x34\x56"})
        assert NothingParser().parse(ad) is None

    def test_identity_uses_persistent_id(self):
        ad = _make_ad(manufacturer_data=_nothing_mfr(payload=b"\xaa\xbb\xcc\xdd\xee\xff"),
                      mac_address="11:22:33:44:55:66")
        result = NothingParser().parse(ad)
        expected = hashlib.sha256(b"nothing:aabbccddeeff").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_returns_none_unrelated(self):
        assert NothingParser().parse(_make_ad(local_name="Other")) is None

    def test_parse_basics(self):
        result = NothingParser().parse(_make_ad(local_name="Nothing ear (1)"))
        assert result.parser_name == "nothing"
        assert result.device_class == "audio"
