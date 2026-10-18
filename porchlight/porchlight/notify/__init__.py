"""Notifiers and the dispatcher that feeds them (SPEC §4.11).

A failing notifier never blocks the pipeline: submit() only queues, each
delivery runs as its own task with a timeout, and failures are retried a few
times before the alert is dropped and logged.
"""

from __future__ import annotations

import asyncio
import logging

from ..config import Notify
from ..model import SEVERITY_RANK
from .base import Notifier

logger = logging.getLogger(__name__)


def build_notifiers(cfgs: list[Notify]) -> list[tuple[Notifier, str]]:
    from .log import LogNotifier

    kinds = {"log": LogNotifier}
    try:
        from .ntfy import NtfyNotifier
        from .webhook import WebhookNotifier
        from .mqtt import MqttNotifier
        kinds.update(ntfy=NtfyNotifier, webhook=WebhookNotifier, mqtt=MqttNotifier)
    except ImportError:
        pass
    out = []
    for c in cfgs:
        if c.type == "page":
            continue  # the page is always on: it reads the engine directly
        if c.type not in kinds:
            raise ValueError(f"unknown notifier type {c.type!r}")
        out.append((kinds[c.type](c), c.min_severity))
    return out


class Dispatcher:
    def __init__(self, notifiers: list[tuple[Notifier, str]], retries: int = 3, backoff: float = 2.0,
                 timeout: float = 15.0, queue_max: int = 200):
        self.notifiers = notifiers
        self.retries = retries
        self.backoff = backoff
        self.timeout = timeout
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=queue_max)
        self.dropped = 0
        self._task: asyncio.Task | None = None
        self._inflight: set[asyncio.Task] = set()

    def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
        for t in list(self._inflight):
            t.cancel()
        await asyncio.gather(*self._inflight, *( [self._task] if self._task else []), return_exceptions=True)
        for n, _ in self.notifiers:
            try:
                await n.close()
            except Exception:
                logger.debug("closing %s failed", n.type, exc_info=True)

    def idle(self) -> bool:
        return self.queue.empty() and not self._inflight

    def submit(self, alert: dict) -> None:
        self._put(("alert", alert))

    def submit_armed(self, armed: bool) -> None:
        self._put(("armed", armed))

    def _put(self, item) -> None:
        try:
            self.queue.put_nowait(item)
        except asyncio.QueueFull:
            self.dropped += 1
            logger.error("notification queue full: dropped a %s", item[0])

    async def _run(self) -> None:
        while True:
            kind, payload = await self.queue.get()
            for n, min_sev in self.notifiers:
                if kind == "alert":
                    if payload["severity"] == "info" or SEVERITY_RANK[payload["severity"]] < SEVERITY_RANK[min_sev]:
                        continue
                    coro = lambda n=n, p=payload: n.send(p)
                else:
                    coro = lambda n=n, p=payload: n.armed(p)
                t = asyncio.create_task(self._deliver(n, kind, payload, coro))
                self._inflight.add(t)
                t.add_done_callback(self._inflight.discard)

    async def _deliver(self, n: Notifier, kind: str, payload, coro) -> None:
        for attempt in range(self.retries + 1):
            try:
                await asyncio.wait_for(coro(), timeout=self.timeout)
                return
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning("%s notifier failed (%s, attempt %d/%d): %s", n.type, kind, attempt + 1,
                            self.retries + 1, e or type(e).__name__)
                if attempt < self.retries:
                    await asyncio.sleep(self.backoff * 2 ** attempt)
        what = f"alert {payload['id']}" if kind == "alert" else "armed state"
        logger.error("%s notifier: dropped %s after %d attempts", n.type, what, self.retries + 1)
