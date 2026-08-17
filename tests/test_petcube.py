"""Tests for the Petcube plugin (camera/feeder line + Petcube Tracker).

Source: apk-ble-hunting/reports/petcube-android_passive.md (+ the Stage 4
report's ServiceUuids.java table).
"""

import hashlib

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser

from adwatch.plugins.petcube import (
    PetcubeParser,
    PETCUBE_CAMERA_UUIDS,
    PETCUBE_TRACKER_NAME_PATTERN,
    CAMERA_MODEL_BY_UUID,
)


def _make_ad(**kw):
    defaults = {
        "timestamp": "2025-01-01T00:00:00Z",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "random",
        "manufacturer_data": None,
        "service_data": None,
    }
    defaults.update(kw)
    return RawAdvertisement(**defaults)


def _register(registry):
    @register_parser(
        name="petcube",
        service_uuid=list(PETCUBE_CAMERA_UUIDS),
        local_name_pattern=PETCUBE_TRACKER_NAME_PATTERN,
        description="Petcube",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class _P(PetcubeParser):
        pass

    return _P


class TestPetcubeMatching:
    @pytest.mark.parametrize("uuid", sorted(PETCUBE_CAMERA_UUIDS))
    def test_matches_each_camera_uuid(self, uuid):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(service_uuids=[uuid]))) == 1

    def test_matches_tracker_name(self):
        registry = ParserRegistry()
        _register(registry)
        assert len(registry.match(_make_ad(local_name="TRACKER_A1B2C3D"))) == 1

    def test_no_match_short_tracker_suffix(self):
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(_make_ad(local_name="TRACKER_ABC")) == []

    def test_no_match_unrelated(self):
        registry = ParserRegistry()
        _register(registry)
        assert registry.match(_make_ad(local_name="MyPhone")) == []

    def test_nine_camera_uuids(self):
        assert len(PETCUBE_CAMERA_UUIDS) == 9
        assert set(CAMERA_MODEL_BY_UUID) == set(PETCUBE_CAMERA_UUIDS)


class TestPetcubeCamera:
    def test_basics(self):
        uuid = "e7889b80-48e2-474e-8b6c-b585cc039b77"
        result = PetcubeParser().parse(_make_ad(service_uuids=[uuid]))
        assert result is not None
        assert result.parser_name == "petcube"
        assert result.beacon_type == "petcube"
        assert result.device_class == "camera"
        assert result.metadata["vendor"] == "Petcube"
        assert result.metadata["family"] == "camera"

    def test_model_and_soc_decoded(self):
        result = PetcubeParser().parse(
            _make_ad(service_uuids=["8f22fc9b-c180-43f4-ac04-d5b0a001ae77"])
        )
        assert result.metadata["model"] == "Petcube Play 2"
        assert result.metadata["soc_vendor"] == "Rockchip"

    def test_chicony_variant(self):
        result = PetcubeParser().parse(
            _make_ad(service_uuids=["edc968d2-10e7-4ad8-9b68-2c545aa3e7ca"])
        )
        assert result.metadata["soc_vendor"] == "Chicony"

    def test_setup_mode_flag(self):
        # Cameras only advertise while in Wi-Fi provisioning mode.
        result = PetcubeParser().parse(
            _make_ad(service_uuids=["66971b13-74ee-4ecd-aae8-cac5b756f2b7"])
        )
        assert result.metadata["setup_mode"] is True

    def test_uppercase_uuid_still_matches(self):
        result = PetcubeParser().parse(
            _make_ad(service_uuids=["B5CC439B-CFBD-4088-A606-86FACC6C77FE"])
        )
        assert result is not None
        assert result.metadata["soc_vendor"] == "Rockchip"

    def test_identity_hash_is_mac_based(self):
        uuid = "e7889b80-48e2-474e-8b6c-b585cc039b77"
        result = PetcubeParser().parse(_make_ad(service_uuids=[uuid]))
        expected = hashlib.sha256(b"petcube:cam:AA:BB:CC:DD:EE:FF").hexdigest()[:16]
        assert result.identifier_hash == expected


class TestPetcubeTracker:
    def test_basics(self):
        result = PetcubeParser().parse(_make_ad(local_name="TRACKER_A1B2C3D"))
        assert result is not None
        assert result.device_class == "pet_tracker"
        assert result.metadata["family"] == "tracker"
        assert result.metadata["model"] == "Petcube Tracker"

    def test_suffix_extracted(self):
        result = PetcubeParser().parse(_make_ad(local_name="TRACKER_A1B2C3D"))
        assert result.metadata["tracker_id"] == "A1B2C3D"

    def test_identity_hash_uses_suffix_not_mac(self):
        # The 7-char suffix is durable across MAC randomisation.
        a = PetcubeParser().parse(_make_ad(local_name="TRACKER_A1B2C3D"))
        b = PetcubeParser().parse(
            _make_ad(local_name="TRACKER_A1B2C3D", mac_address="11:22:33:44:55:66")
        )
        assert a.identifier_hash == b.identifier_hash
        expected = hashlib.sha256(b"petcube:tracker:A1B2C3D").hexdigest()[:16]
        assert a.identifier_hash == expected

    def test_different_suffix_different_hash(self):
        a = PetcubeParser().parse(_make_ad(local_name="TRACKER_A1B2C3D"))
        b = PetcubeParser().parse(_make_ad(local_name="TRACKER_ZZZZZZZ"))
        assert a.identifier_hash != b.identifier_hash

    def test_stable_key_is_suffix(self):
        result = PetcubeParser().parse(_make_ad(local_name="TRACKER_A1B2C3D"))
        assert result.stable_key == "petcube:tracker:A1B2C3D"

    def test_wrong_length_suffix_rejected(self):
        assert PetcubeParser().parse(_make_ad(local_name="TRACKER_TOOLONGSUFFIX")) is None
        assert PetcubeParser().parse(_make_ad(local_name="TRACKER_ABC")) is None

    def test_returns_none_unrelated(self):
        assert PetcubeParser().parse(_make_ad(local_name="Tracker")) is None
        assert PetcubeParser().parse(_make_ad()) is None
