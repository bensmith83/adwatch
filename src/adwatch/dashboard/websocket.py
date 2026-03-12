"""WebSocket event broadcasting for adwatch dashboard."""

from __future__ import annotations

import asyncio
import dataclasses
import json
import logging

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections and broadcasts events."""

    def __init__(self):
        self._connections: list = []

    async def connect(self, websocket) -> None:
        await websocket.accept()
        self._connections.append(websocket)

    async def disconnect(self, websocket) -> None:
        if websocket in self._connections:
            self._connections.remove(websocket)

    async def emit(self, event_type: str, data) -> None:
        payload = {"type": event_type, "data": _serialize(data)}
        dead = []
        for ws in self._connections:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections.remove(ws)


class ThrottledEmitter:
    """Wraps WebSocketManager, buffering sighting events into batches."""

    _BUFFERED_EVENTS = frozenset({"sighting"})

    def __init__(self, manager: WebSocketManager, flush_interval: float = 0.25):
        self._manager = manager
        self._flush_interval = flush_interval
        self._buffer: list = []
        self._task: asyncio.Task | None = None

    async def connect(self, websocket) -> None:
        await self._manager.connect(websocket)

    async def disconnect(self, websocket) -> None:
        await self._manager.disconnect(websocket)

    async def emit(self, event_type: str, data) -> None:
        if event_type in self._BUFFERED_EVENTS:
            self._buffer.append(data)
        else:
            await self._manager.emit(event_type, data)

    async def start(self) -> None:
        self._task = asyncio.create_task(self._flush_loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        await self._flush()

    async def _flush_loop(self) -> None:
        while True:
            await asyncio.sleep(self._flush_interval)
            await self._flush()

    async def _flush(self) -> None:
        if not self._buffer:
            return
        batch = self._buffer[:]
        self._buffer.clear()
        await self._manager.emit("sighting_batch", batch)


def _serialize(obj):
    """Convert dataclasses and bytes to JSON-safe dicts."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        from adwatch.models import RawAdvertisement
        d = {k: _serialize(v) for k, v in dataclasses.asdict(obj).items()}
        if isinstance(obj, RawAdvertisement):
            d["mac_type"] = obj.mac_type
        return d
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(i) for i in obj]
    if isinstance(obj, bytes):
        return obj.hex()
    return obj
