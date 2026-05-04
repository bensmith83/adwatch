"""Tests for Jabra (GN Netcom) plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.jabra import JabraParser, JABRA_SERVICE_UUID


def _make_ad(**kw):
    defaults = {"timestamp": "2025-01-01T00:00:00Z", "mac_address": "AA:BB:CC:DD:EE:FF",
                "address_type": "random", "manufacturer_data": None, "service_data": None}
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(name="jabra", service_uuid=JABRA_SERVICE_UUID,
                     local_name_pattern=r"^Jabra ", description="Jabra",
                     version="1.0.0", core=False, registry=registry)
    class _P(JabraParser):
        pass
    return _P


def _jabra_mfr(serv_type=0x10, product_id=0x3010, unique_id=0xDEADBEEF, tx_power=-59):
    """Build mfr-data with arbitrary CID + 8-byte Jabra payload."""
    cid = b"\x00\x00"
    payload = bytes([
        serv_type,
        product_id & 0xFF,
        (product_id >> 8) & 0xFF,
        unique_id & 0xFF,
        (unique_id >> 8) & 0xFF,
        (unique_id >> 16) & 0xFF,
        (unique_id >> 24) & 0xFF,
        tx_power & 0xFF,
    ])
    return cid + payload


class TestJabraMatching:
    def test_match_uuid(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(service_uuids=[JABRA_SERVICE_UUID])
        assert len(registry.match(ad)) == 1

    def test_match_name(self):
        registry = ParserRegistry()
        _register(registry)
        ad = _make_ad(local_name="Jabra Elite 75t")
        assert len(registry.match(ad)) == 1


class TestJabraParsing:
    def test_product_family_evolve(self):
        ad = _make_ad(service_uuids=[JABRA_SERVICE_UUID],
                       manufacturer_data=_jabra_mfr(product_id=0x3010))
        result = JabraParser().parse(ad)
        assert result.metadata["product_family"] == "Evolve"
        assert result.metadata["product_id"] == 0x3010

    def test_unique_id_extraction(self):
        ad = _make_ad(service_uuids=[JABRA_SERVICE_UUID],
                       manufacturer_data=_jabra_mfr(unique_id=0xCAFEBABE))
        result = JabraParser().parse(ad)
        assert result.metadata["unique_id"] == 0xCAFEBABE
        assert result.metadata["unique_id_hex"] == "cafebabe"

    def test_tx_power_signed(self):
        ad = _make_ad(service_uuids=[JABRA_SERVICE_UUID],
                       manufacturer_data=_jabra_mfr(tx_power=-59))
        result = JabraParser().parse(ad)
        assert result.metadata["tx_power"] == -59

    def test_identity_uses_unique_id(self):
        ad = _make_ad(service_uuids=[JABRA_SERVICE_UUID],
                       manufacturer_data=_jabra_mfr(unique_id=0x12345678),
                       mac_address="11:22:33:44:55:66")
        result = JabraParser().parse(ad)
        expected = hashlib.sha256(b"jabra:12345678").hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_returns_none_unrelated(self):
        assert JabraParser().parse(_make_ad(local_name="Other")) is None

    def test_parse_basics(self):
        result = JabraParser().parse(_make_ad(service_uuids=[JABRA_SERVICE_UUID]))
        assert result.parser_name == "jabra"
        assert result.device_class == "audio"
