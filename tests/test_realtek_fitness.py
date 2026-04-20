"""Tests for the generic Realtek/chipset OEM fitness-band parser (0AF0)."""

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.realtek_fitness import (
    RealtekFitnessParser,
    RTK_FITNESS_SERVICE_UUID,
)


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


def _make_registry():
    registry = ParserRegistry()

    @register_parser(
        name="realtek_fitness",
        service_uuid=RTK_FITNESS_SERVICE_UUID,
        description="Realtek/OEM white-label fitness watch (0x0AF0 family)",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(RealtekFitnessParser):
        pass

    return registry


class TestRealtekFitnessRegistry:
    def test_matches_0af0_service_uuid(self):
        registry = _make_registry()
        ad = _make_ad(service_uuids=["0af0"])
        assert len(registry.match(ad)) >= 1

    def test_no_match_unrelated(self):
        registry = _make_registry()
        ad = _make_ad(local_name="Kettle")
        assert len(registry.match(ad)) == 0


class TestRealtekFitnessParser:
    def test_biggerfive_brave2(self):
        parser = RealtekFitnessParser()
        ad = _make_ad(
            local_name="BIGGERFIVE Brave 2",
            service_uuids=["0af0"],
            manufacturer_data=bytes.fromhex("ab1ef406c88a7136020107010101"),
        )
        result = parser.parse(ad)
        assert result is not None
        assert result.parser_name == "realtek_fitness"
        assert result.device_class == "fitness_watch"
        assert result.metadata["device_name"] == "BIGGERFIVE Brave 2"
        # BLE CIDs are little-endian: raw bytes 0xAB 0x1E -> CID 0x1EAB
        assert result.metadata["vendor_cid"] == 0x1EAB
        # 6 embedded ID bytes (MAC-shaped)
        assert result.metadata["device_id"] == "f4:06:c8:8a:71:36"

    def test_idw20(self):
        parser = RealtekFitnessParser()
        ad = _make_ad(
            local_name="IDW20",
            service_uuids=["0af0"],
            manufacturer_data=bytes.fromhex("331ff43aa22dea34020101010101"),
        )
        result = parser.parse(ad)
        assert result is not None
        assert result.metadata["vendor_cid"] == 0x1F33
        assert result.metadata["device_id"] == "f4:3a:a2:2d:ea:34"

    def test_status_byte_exposed(self):
        """Byte offset 10 (after CID+MAC+02+01) looks like a varying status/state."""
        parser = RealtekFitnessParser()
        ad = _make_ad(
            service_uuids=["0af0"],
            manufacturer_data=bytes.fromhex("ab1ef406c88a7136020107010101"),
        )
        result = parser.parse(ad)
        assert result.metadata["state_byte"] == 0x07

    def test_identity_hash_uses_embedded_id(self):
        """Identity should key off the *embedded* ID (which is stable), not
        the outer BLE MAC which may be randomized. Both ads with the same
        embedded ID must produce the same identifier_hash."""
        parser = RealtekFitnessParser()
        payload = "ab1ef406c88a7136020107010101"
        a = _make_ad(
            mac_address="AA:BB:CC:DD:EE:01",
            service_uuids=["0af0"],
            manufacturer_data=bytes.fromhex(payload),
        )
        b = _make_ad(
            mac_address="AA:BB:CC:DD:EE:02",
            service_uuids=["0af0"],
            manufacturer_data=bytes.fromhex(payload),
        )
        assert parser.parse(a).identifier_hash == parser.parse(b).identifier_hash

    def test_rejects_unrelated_service_uuid(self):
        parser = RealtekFitnessParser()
        ad = _make_ad(
            service_uuids=["feaa"],
            manufacturer_data=bytes.fromhex("ab1ef406c88a7136020107010101"),
        )
        assert parser.parse(ad) is None

    def test_short_payload_still_records_presence(self):
        """If mfg data is too short for the full layout, still record the
        service-UUID sighting but don't invent fields."""
        parser = RealtekFitnessParser()
        ad = _make_ad(
            service_uuids=["0af0"],
            manufacturer_data=bytes.fromhex("ab1e"),
        )
        result = parser.parse(ad)
        assert result is not None
        assert "device_id" not in result.metadata
        assert "vendor_cid" not in result.metadata

    def test_rejects_wrong_shape(self):
        """Right service UUID but mfg payload doesn't have the 0x02 0x01 pivot."""
        parser = RealtekFitnessParser()
        ad = _make_ad(
            service_uuids=["0af0"],
            manufacturer_data=bytes.fromhex("ab1ef406c88a7136ff00ff00ff00"),
        )
        # Should still return *something* (we saw the service UUID) but with
        # no extracted fields — so assert we gracefully degrade.
        result = parser.parse(ad)
        assert result is not None
        assert "device_id" not in result.metadata
