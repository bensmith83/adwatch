"""Scanner ads -> parser -> engine, in order.

Ads queue up (bounded; overflow is dropped and counted). They are taken in
batches: payloads not in the parse cache go to the sidecar concurrently (it
answers in order), then the whole batch is ingested in arrival order.
"""

from __future__ import annotations

import asyncio
import logging

from .engine import Engine
from .sidecar import ParseCache

log = logging.getLogger(__name__)


class Pipeline:
    def __init__(self, engine: Engine, parse, cache: ParseCache | None = None, capture=None,
                 queue_max: int = 5000, batch: int = 256):
        self.engine = engine
        self.parse = parse
        self.cache = cache or ParseCache()
        self.capture = capture
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=queue_max)
        self.batch = batch
        self.dropped = 0

    def offer(self, ad: dict) -> bool:
        """From the scanner callback: never blocks."""
        if self.capture is not None:
            try:
                self.capture.write(ad)
            except OSError:
                log.warning("capture write failed", exc_info=True)
        try:
            self.queue.put_nowait(ad)
            return True
        except asyncio.QueueFull:
            self.dropped += 1
            if self.dropped % 1000 == 1:
                log.warning("ad queue full: %d ads dropped so far", self.dropped)
            return False

    async def parse_all(self, ads: list[dict]) -> list:
        results: list = [None] * len(ads)
        misses: dict[str, list[int]] = {}
        for i, a in enumerate(ads):
            hit = self.cache.get(a)
            if hit is not None:
                results[i] = hit
            else:
                misses.setdefault(ParseCache.key(a), []).append(i)
        parsed = await asyncio.gather(*(self.parse(ads[idx[0]]) for idx in misses.values()))
        for idx, res in zip(misses.values(), parsed):
            if res is not None:
                self.cache.put(ads[idx[0]], res)
            for i in idx:
                results[i] = res
        return results

    async def process(self, ads: list[dict]) -> None:
        for a, res in zip(ads, await self.parse_all(ads)):
            if res is None:
                self.dropped += 1
                continue
            self.engine.ingest(a, res)

    async def run(self) -> None:
        while True:
            batch = [await self.queue.get()]
            while len(batch) < self.batch and not self.queue.empty():
                batch.append(self.queue.get_nowait())
            try:
                await self.process(batch)
            except Exception:
                log.exception("pipeline error; batch of %d ads skipped", len(batch))
