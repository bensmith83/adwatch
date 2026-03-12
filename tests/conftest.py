"""Shared test fixtures."""

import pytest
from adwatch.models import RawAdvertisement


@pytest.fixture
def apple_nearby_ad():
    """Apple Nearby Info advertisement."""
    return RawAdvertisement(
        timestamp="2025-01-15T10:30:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        manufacturer_data=b"\x4c\x00\x10\x05\x01\x18\x44\x00\x00",
        service_data=None,
        service_uuids=[],
        local_name=None,
        rssi=-62,
        tx_power=None,
    )


@pytest.fixture
def thermopro_ad():
    """ThermoPro temperature sensor advertisement."""
    return RawAdvertisement(
        timestamp="2025-01-15T10:30:00+00:00",
        mac_address="11:22:33:44:55:66",
        address_type="random",
        manufacturer_data=None,
        service_data=None,
        service_uuids=[],
        local_name="TP357 (2B54)",
        rssi=-45,
        tx_power=None,
    )


@pytest.fixture
def ibeacon_ad():
    """iBeacon advertisement."""
    # company_id 0x004C + subtype 0x02 + length 0x15 + UUID(16) + Major(2) + Minor(2) + TX(1)
    uuid_bytes = bytes.fromhex("B9407F30F5F8466EAFF925556B57FE6D")
    payload = b"\x4c\x00\x02\x15" + uuid_bytes + b"\x00\x01\x00\x02\xC5"
    return RawAdvertisement(
        timestamp="2025-01-15T10:30:00+00:00",
        mac_address="DE:AD:BE:EF:00:01",
        address_type="random",
        manufacturer_data=payload,
        service_data=None,
        service_uuids=[],
        local_name=None,
        rssi=-71,
        tx_power=None,
    )


@pytest.fixture
def fast_pair_ad():
    """Google Fast Pair advertisement."""
    return RawAdvertisement(
        timestamp="2025-01-15T10:30:00+00:00",
        mac_address="FA:57:PA:1R:00:01",
        address_type="random",
        manufacturer_data=None,
        service_data={"0000fe2c-0000-1000-8000-00805f9b34fb": b"\xAA\xBB\xCC"},
        service_uuids=["0000fe2c-0000-1000-8000-00805f9b34fb"],
        local_name=None,
        rssi=-60,
        tx_power=None,
    )


@pytest.fixture
def microsoft_cdp_ad():
    """Microsoft CDP advertisement."""
    return RawAdvertisement(
        timestamp="2025-01-15T10:30:00+00:00",
        mac_address="MS:CD:P0:00:00:01",
        address_type="random",
        manufacturer_data=b"\x06\x00\x01\x09\x20\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
        service_data=None,
        service_uuids=[],
        local_name=None,
        rssi=-55,
        tx_power=None,
    )


@pytest.fixture
def unknown_ad():
    """Unknown/unclassified advertisement."""
    return RawAdvertisement(
        timestamp="2025-01-15T10:30:00+00:00",
        mac_address="00:11:22:33:44:55",
        address_type="public",
        manufacturer_data=b"\xFF\xFF\x01\x02\x03",
        service_data=None,
        service_uuids=[],
        local_name=None,
        rssi=-80,
        tx_power=None,
    )
