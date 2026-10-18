"""`mqtt`: publishes alerts and the armed state, with optional Home Assistant
discovery. A minimal MQTT 3.1.1 publisher (QoS 0) on asyncio streams, since
the runtime dependencies are bleak and aiohttp only.

Topics, under topic_prefix (default "porchlight"):
  <prefix>/alert    each alert as JSON
  <prefix>/armed    ON / OFF, retained
  <prefix>/status   online / offline (the last will), retained
"""

from __future__ import annotations

import asyncio
import json
import logging
import os

from ..config import Notify
from .base import Notifier

log = logging.getLogger(__name__)

CONNECT, CONNACK, PUBLISH, PINGREQ, DISCONNECT = 0x10, 0x20, 0x30, 0xC0, 0xE0
KEEPALIVE_S = 60


def _varint(n: int) -> bytes:
    out = bytearray()
    while True:
        b, n = n % 128, n // 128
        out.append(b | (0x80 if n else 0))
        if not n:
            return bytes(out)


def _str(s: str | bytes) -> bytes:
    b = s.encode() if isinstance(s, str) else s
    return len(b).to_bytes(2, "big") + b


def packet(head: int, body: bytes = b"") -> bytes:
    return bytes([head]) + _varint(len(body)) + body


class MqttNotifier(Notifier):
    type = "mqtt"

    def __init__(self, cfg: Notify):
        o = cfg.options
        self.host = o.get("host")
        if not self.host:
            raise ValueError("mqtt notifier needs a host")
        self.port = int(o.get("port", 1883))
        self.username = o.get("username") or ""
        self.password = o.get("password") or ""
        self.prefix = (o.get("topic_prefix") or "porchlight").rstrip("/")
        self.discovery = bool(o.get("discovery", False))
        self.discovery_prefix = (o.get("discovery_prefix") or "homeassistant").rstrip("/")
        self.client_id = o.get("client_id") or f"porchlight-{os.getpid()}"
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._tasks: list[asyncio.Task] = []
        self._lock = asyncio.Lock()
        self._armed: bool | None = None

    # --- connection ------------------------------------------------------------

    def _connected(self) -> bool:
        return self._writer is not None and not self._writer.is_closing() and not self._reader.at_eof()

    async def _connect(self) -> None:
        await self._drop()
        reader, writer = await asyncio.wait_for(asyncio.open_connection(self.host, self.port), timeout=10)
        flags = 0x02 | 0x04 | 0x20          # clean session, will, will retain
        payload = _str(self.client_id) + _str(f"{self.prefix}/status") + _str("offline")
        if self.username:
            flags |= 0x80
            payload += _str(self.username)
            if self.password:
                flags |= 0x40
                payload += _str(self.password)
        body = _str("MQTT") + bytes([4, flags]) + KEEPALIVE_S.to_bytes(2, "big") + payload
        writer.write(packet(CONNECT, body))
        await writer.drain()
        ack = await asyncio.wait_for(reader.readexactly(4), timeout=10)
        if ack[0] != CONNACK or ack[3] != 0:
            writer.close()
            raise ConnectionError(f"MQTT broker refused the connection (code {ack[3]})")
        self._reader, self._writer = reader, writer
        self._tasks = [asyncio.create_task(self._ping()), asyncio.create_task(self._discard(reader))]
        await self._publish(f"{self.prefix}/status", b"online", retain=True)
        if self.discovery:
            for topic, cfg in self._discovery_configs():
                await self._publish(topic, json.dumps(cfg).encode(), retain=True)
        if self._armed is not None:
            await self._publish(f"{self.prefix}/armed", b"ON" if self._armed else b"OFF", retain=True)
        log.info("connected to MQTT broker %s:%d", self.host, self.port)

    async def _ping(self) -> None:
        try:
            while True:
                await asyncio.sleep(KEEPALIVE_S / 2)
                self._writer.write(packet(PINGREQ))
                await self._writer.drain()
        except (asyncio.CancelledError, ConnectionError, AttributeError):
            pass

    @staticmethod
    async def _discard(reader: asyncio.StreamReader) -> None:
        """Read and drop what the broker sends (PINGRESPs) so the buffer never
        fills; EOF here is how a dropped connection shows up."""
        try:
            while await reader.read(1024):
                pass
        except (asyncio.CancelledError, ConnectionError):
            pass

    async def _drop(self) -> None:
        for t in self._tasks:
            t.cancel()
        self._tasks = []
        if self._writer is not None:
            self._writer.close()
        self._reader = self._writer = None

    async def _publish(self, topic: str, payload: bytes, retain: bool = False) -> None:
        self._writer.write(packet(PUBLISH | (0x01 if retain else 0), _str(topic) + payload))
        await self._writer.drain()

    async def _send(self, topic: str, payload: bytes, retain: bool = False) -> None:
        async with self._lock:
            if not self._connected():
                await self._connect()
            try:
                await self._publish(topic, payload, retain)
            except (ConnectionError, OSError):
                await self._drop()
                raise

    def _discovery_configs(self):
        device = {"identifiers": ["porchlight"], "name": "Porchlight", "model": "BLE home alarm"}
        avail = f"{self.prefix}/status"
        yield (f"{self.discovery_prefix}/binary_sensor/porchlight/armed/config",
               {"name": "Porchlight armed", "unique_id": "porchlight_armed", "state_topic": f"{self.prefix}/armed",
                "payload_on": "ON", "payload_off": "OFF", "availability_topic": avail, "device": device,
                "icon": "mdi:shield-home"})
        yield (f"{self.discovery_prefix}/sensor/porchlight/last_alert/config",
               {"name": "Porchlight last alert", "unique_id": "porchlight_last_alert",
                "state_topic": f"{self.prefix}/alert", "value_template": "{{ value_json.title }}",
                "json_attributes_topic": f"{self.prefix}/alert", "availability_topic": avail, "device": device,
                "icon": "mdi:alarm-light"})

    # --- the notifier interface -------------------------------------------------------

    async def send(self, alert: dict) -> None:
        await self._send(f"{self.prefix}/alert", json.dumps(alert).encode())

    async def armed(self, armed: bool) -> None:
        self._armed = armed
        await self._send(f"{self.prefix}/armed", b"ON" if armed else b"OFF", retain=True)

    async def close(self) -> None:
        if self._connected():
            try:
                await self._publish(f"{self.prefix}/status", b"offline", retain=True)
                self._writer.write(packet(DISCONNECT))
                await self._writer.drain()
            except (ConnectionError, OSError):
                pass
        await self._drop()
