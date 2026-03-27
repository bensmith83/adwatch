"""BLE advertisement scanner using bleak."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import asyncio

from adwatch.models import RawAdvertisement

logger = logging.getLogger(__name__)


class Scanner:
    def __init__(self, adapter: str | None = None):
        self._adapter = adapter or "hci0"
        self._scanner = None
        self._callback = None

    async def start(self, callback) -> None:
        from bleak import BleakScanner

        self._callback = callback

        def _handle_task_exception(task):
            if not task.cancelled() and task.exception():
                logger.error("Pipeline callback error: %s", task.exception())

        def _detection_callback(device, advertisement_data):
            manufacturer_data = None
            for company_id, data in advertisement_data.manufacturer_data.items():
                manufacturer_data = company_id.to_bytes(2, "little") + data
                break

            service_data = dict(advertisement_data.service_data)

            # Get address type from BlueZ D-Bus properties if available
            address_type = "random"
            try:
                props = device.details.get("props", {})
                if props.get("AddressType", "") == "public":
                    address_type = "public"
            except (AttributeError, TypeError):
                pass

            raw = RawAdvertisement(
                timestamp=datetime.now(timezone.utc).isoformat(),
                mac_address=device.address,
                address_type=address_type,
                manufacturer_data=manufacturer_data,
                service_data=service_data or None,
                service_uuids=advertisement_data.service_uuids or [],
                local_name=advertisement_data.local_name,
                rssi=advertisement_data.rssi,
                tx_power=advertisement_data.tx_power,
            )
            task = asyncio.create_task(callback(raw))
            task.add_done_callback(_handle_task_exception)

        self._scanner = BleakScanner(
            detection_callback=_detection_callback,
            adapter=self._adapter,
        )
        try:
            await self._scanner.start()
            logger.info("BLE scanner started on %s", self._adapter)
        except Exception as exc:
            logger.error("BLE scanner failed to start on %s: %s", self._adapter, exc)
            self._scanner = None
            raise

    async def stop(self) -> None:
        if self._scanner:
            try:
                await self._scanner.stop()
            except Exception:
                logger.warning("Error stopping BLE scanner", exc_info=True)
            self._scanner = None
