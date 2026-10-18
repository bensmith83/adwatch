"""Replay a capture through the whole pipeline on a simulated clock (SPEC §4.12).

The clock is the ads' own timestamps: the engine ticks every tick_step of
simulated time, including through quiet stretches, so visits close and
arming changes at the times they would have live. No Bluetooth is involved.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path

from .engine import Engine
from .pipeline import Pipeline

log = logging.getLogger(__name__)


@dataclass
class ReplayStats:
    ads: int = 0
    bad_lines: int = 0
    dropped: int = 0
    first: float | None = None
    last: float | None = None


def _chunks(path: Path, size: int, stats: ReplayStats):
    chunk = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ad = json.loads(line)
                ad["t"], ad["addr"]
            except (ValueError, KeyError, TypeError):
                stats.bad_lines += 1
                continue
            chunk.append(ad)
            if len(chunk) >= size:
                yield chunk
                chunk = []
    if chunk:
        yield chunk


async def replay(path: str | Path, engine: Engine, parse, speed: str = "max", tick_step: float = 5.0,
                 drain: bool = True, batch: int = 256) -> ReplayStats:
    if speed not in ("max", "1x"):
        raise ValueError("speed must be max or 1x")
    stats = ReplayStats()
    pipeline = Pipeline(engine, parse)
    loop = asyncio.get_running_loop()
    last_tick: float | None = None
    wall0 = sim0 = None

    def advance(t: float) -> None:
        nonlocal last_tick
        if last_tick is None:
            last_tick = t
            engine.tick(t)
            return
        while t - last_tick >= tick_step:
            last_tick += tick_step
            engine.tick(last_tick)

    for chunk in _chunks(Path(path), batch, stats):
        results = await pipeline.parse_all(chunk)
        for ad, res in zip(chunk, results):
            t = ad["t"] / 1000.0
            stats.ads += 1
            stats.first = t if stats.first is None else stats.first
            stats.last = t
            if speed == "1x":
                if wall0 is None:
                    wall0, sim0 = loop.time(), t
                delay = (t - sim0) - (loop.time() - wall0)
                if delay > 0:
                    await asyncio.sleep(delay)
            advance(t)
            if res is None:
                stats.dropped += 1
                continue
            engine.ingest(ad, res)
    if drain and stats.last is not None:
        end = stats.last + engine.visits.gap + 2 * tick_step
        advance(end)
        engine.tick(end)
    engine.shutdown()
    return stats
