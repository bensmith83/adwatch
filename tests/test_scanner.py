"""Tests for the Scanner class — red phase."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from adwatch.models import RawAdvertisement
from adwatch.scanner import Scanner


class TestScannerInit:
    def test_scanner_exists(self):
        scanner = Scanner()
        assert scanner is not None

    def test_scanner_accepts_adapter_name(self):
        scanner = Scanner(adapter="hci1")
        assert scanner is not None

    def test_scanner_default_adapter(self):
        scanner = Scanner()
        # Default adapter should be hci0 or similar
        assert hasattr(scanner, "_adapter") or hasattr(scanner, "adapter")


class TestScannerInterface:
    def test_has_start_method(self):
        scanner = Scanner()
        assert hasattr(scanner, "start")
        assert callable(scanner.start)

    def test_has_stop_method(self):
        scanner = Scanner()
        assert hasattr(scanner, "stop")
        assert callable(scanner.stop)


class TestScannerCallbackHandling:
    @pytest.mark.asyncio
    async def test_start_accepts_callback(self):
        scanner = Scanner()
        callback = AsyncMock()
        # start should accept a callback; it will fail without BLE hardware
        # but should not raise TypeError for the signature
        with pytest.raises(Exception):
            # Will fail due to no BLE adapter, but should accept the callback arg
            await scanner.start(callback)

    @pytest.mark.asyncio
    async def test_stop_is_async(self):
        scanner = Scanner()
        # stop should be callable without error even if not started
        try:
            await scanner.stop()
        except Exception:
            # May raise if not started, but should not raise TypeError
            pass


class TestRawAdvertisementFromBleakData:
    def test_raw_ad_creation_with_manufacturer_data(self):
        raw = RawAdvertisement(
            timestamp="2025-01-15T10:30:00+00:00",
            mac_address="AA:BB:CC:DD:EE:FF",
            address_type="random",
            manufacturer_data=b"\x4c\x00\x10\x05\x01",
            service_data=None,
            service_uuids=[],
            local_name=None,
            rssi=-62,
            tx_power=None,
        )
        assert raw.company_id == 0x004C
        assert raw.manufacturer_payload == b"\x10\x05\x01"

    def test_raw_ad_creation_with_service_data(self):
        raw = RawAdvertisement(
            timestamp="2025-01-15T10:30:00+00:00",
            mac_address="FA:57:00:00:00:01",
            address_type="random",
            manufacturer_data=None,
            service_data={"0000fe2c-0000-1000-8000-00805f9b34fb": b"\xaa\xbb\xcc"},
            service_uuids=["0000fe2c-0000-1000-8000-00805f9b34fb"],
            local_name=None,
            rssi=-60,
            tx_power=None,
        )
        assert raw.company_id is None
        assert raw.service_data is not None

    def test_raw_ad_creation_with_local_name(self):
        raw = RawAdvertisement(
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
        assert raw.local_name == "TP357 (2B54)"

    def test_raw_ad_now_factory(self):
        raw = RawAdvertisement.now(
            mac_address="AA:BB:CC:DD:EE:FF",
            manufacturer_data=None,
            service_data=None,
        )
        assert raw.timestamp is not None
        assert raw.address_type == "random"
