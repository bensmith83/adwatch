"""BLE scanning with bleak on BlueZ (SPEC §4.2).

Active scanning (bleak's default), so local names in scan responses arrive.
Duplicate filtering is turned off (BlueZ DuplicateData) so a device sitting
still keeps producing callbacks, which dwell time depends on; a per-payload
throttle then keeps the rate sane. The address type is read from BlueZ's
device properties, the way adwatch does it.
"""

from __future__ import annotations

import logging
import time

from .sidecar import ParseCache

log = logging.getLogger(__name__)


def to_ad(device, adv, now_ms: int) -> dict:
    """One bleak callback -> one ble-parse input line (as a dict)."""
    mfr = None
    for company_id, data in (adv.manufacturer_data or {}).items():
        mfr = (company_id.to_bytes(2, "little") + bytes(data)).hex()
        break
    atype = "random"
    try:
        if (device.details or {}).get("props", {}).get("AddressType", "") == "public":
            atype = "public"
    except (AttributeError, TypeError):
        pass
    return {
        "t": now_ms,
        "addr": device.address,
        "atype": atype,
        "rssi": adv.rssi,
        "mfr": mfr,
        "svc": {uuid: bytes(data).hex() for uuid, data in (adv.service_data or {}).items()},
        "uuids": list(adv.service_uuids or []),
        "name": adv.local_name,
        "tx": adv.tx_power,
    }


class Throttle:
    """At most one sighting per interval for each (address, payload)."""

    def __init__(self, interval: float = 1.0):
        self.interval = interval
        self._last: dict[str, float] = {}

    def allow(self, ad: dict, now: float) -> bool:
        k = ParseCache.key(ad)
        last = self._last.get(k)
        if last is not None and now - last < self.interval:
            return False
        self._last[k] = now
        return True

    def prune(self, now: float) -> None:
        self._last = {k: t for k, t in self._last.items() if now - t < 60 * self.interval}

    def __len__(self) -> int:
        return len(self._last)


class Scanner:
    def __init__(self, adapter: str, on_ad, throttle_s: float = 1.0, scanner_cls=None):
        self.adapter = adapter
        self.scanner_cls = scanner_cls
        self.on_ad = on_ad
        self.throttle = Throttle(throttle_s)
        self._scanner = None
        self.callbacks = 0

    async def start(self) -> None:
        scanner_cls = self.scanner_cls
        if scanner_cls is None:
            from bleak import BleakScanner as scanner_cls

        def callback(device, adv):
            self.callbacks += 1
            now = time.time()
            ad = to_ad(device, adv, int(now * 1000))
            if self.throttle.allow(ad, now):
                self.on_ad(ad)
            if self.callbacks % 10000 == 0:
                self.throttle.prune(now)

        self._scanner = scanner_cls(
            detection_callback=callback,
            scanning_mode="active",
            bluez={"adapter": self.adapter, "filters": {"DuplicateData": True}},
        )
        try:
            await self._scanner.start()
        except Exception as e:
            self._scanner = None
            raise RuntimeError(f"cannot start BLE scanning on {self.adapter}: {e or type(e).__name__}. Is "
                               "bluetoothd running (and D-Bus), does the adapter exist (bluetoothctl list), "
                               "and is this user in the bluetooth group?") from e
        log.info("scanning on %s", self.adapter)

    async def stop(self) -> None:
        if self._scanner:
            try:
                await self._scanner.stop()
            except Exception:
                log.warning("error stopping the scanner", exc_info=True)
            self._scanner = None
