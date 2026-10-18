import asyncio
import json

import pytest

from fakes import T0, TABLE, TZ, ad, watch
from porchlight.config import Config
from porchlight.engine import Engine
from porchlight.pipeline import Pipeline
from porchlight.replay import replay
from porchlight.store import Store


def engine_for(tmp_path, **kw):
    cfg = Config()
    cfg.learning.learning_days = kw.pop("learning_days", 0)
    for k, v in kw.items():
        section, key = k.split("__")
        setattr(getattr(cfg, section), key, v)
    return Engine(cfg, TABLE, Store(tmp_path / "p.db"), now=T0, tz=TZ)


class FakeParse:
    """Stands in for the sidecar: a name of 'W<serial>' parses as a watch."""

    def __init__(self, down=False):
        self.calls = 0
        self.down = down

    async def __call__(self, a):
        self.calls += 1
        await asyncio.sleep(0)
        if self.down:
            return None
        name = a.get("name") or ""
        return watch(name[1:]) if name.startswith("W") else []


async def test_pipeline_ingests_in_order_and_caches_parses(tmp_path):
    engine = engine_for(tmp_path)
    parse = FakeParse()
    p = Pipeline(engine, parse)
    ads = [ad(T0 + i, name="WTEST0001", rssi=-60 - i % 3) for i in range(20)]
    await p.process(ads)
    (u,) = engine.units.units.values()
    v = engine.visits.open[u.id]
    assert v.n == 20 and v.start == T0 and v.end == T0 + 19
    assert parse.calls == 1, "same payload: parsed once"


async def test_pipeline_drops_ads_the_parser_could_not_answer(tmp_path):
    engine = engine_for(tmp_path)
    p = Pipeline(engine, FakeParse(down=True))
    await p.process([ad(T0, name="WTEST0001")])
    assert engine.units.units == {}
    assert p.dropped == 1


async def test_offer_queues_and_drops_when_full(tmp_path):
    engine = engine_for(tmp_path)
    p = Pipeline(engine, FakeParse(), queue_max=3)
    assert all(p.offer(ad(T0 + i)) for i in range(3))
    assert not p.offer(ad(T0 + 3))
    assert p.dropped == 1


async def test_offer_tees_to_the_capture(tmp_path):
    seen = []
    p = Pipeline(engine_for(tmp_path), FakeParse(), capture=type("C", (), {"write": lambda self, a: seen.append(a)})())
    p.offer(ad(T0))
    assert len(seen) == 1


async def test_run_consumes_the_queue(tmp_path):
    engine = engine_for(tmp_path)
    p = Pipeline(engine, FakeParse())
    task = asyncio.create_task(p.run())
    for i in range(5):
        p.offer(ad(T0 + i, name="WTEST0001"))
    for _ in range(100):
        await asyncio.sleep(0.01)
        if engine.units.units and engine.visits.open:
            if next(iter(engine.visits.open.values())).n == 5:
                break
    task.cancel()
    assert next(iter(engine.visits.open.values())).n == 5


def write_capture(path, ads):
    path.write_text("".join(json.dumps(a) + "\n" for a in ads))
    return path


async def test_replay_runs_a_capture_on_a_simulated_clock(tmp_path):
    engine = engine_for(tmp_path)
    cap = write_capture(tmp_path / "c.jsonl", [ad(T0 + 10 * i, name="WTEST0001") for i in range(70)])
    stats = await replay(cap, engine, FakeParse(), speed="max")
    assert stats.ads == 70
    assert [a.rule for a in engine.alerts.alerts.values()] == ["R1"]
    # replay runs past the end so the last visit closes
    assert engine.visits.open == {}
    assert engine.now >= T0 + 690 + 300


async def test_replay_ticks_through_quiet_stretches(tmp_path):
    engine = engine_for(tmp_path, arming__mode="presence")
    seen = []
    engine.on_arming.append(lambda armed: seen.append((engine.now, armed)))
    engine.ingest(ad(T0, name="WTEST0001"), watch())
    engine.label(next(iter(engine.units.units)), "household")
    cap = write_capture(tmp_path / "c.jsonl", [ad(T0 + 1, name="WTEST0001"), ad(T0 + 3600, name="X")])
    await replay(cap, engine, FakeParse(), speed="max")
    (t, armed), = [s for s in seen if s[1]]
    assert armed and T0 + 1 + 900 <= t <= T0 + 1 + 905


async def test_replay_skips_bad_lines(tmp_path):
    engine = engine_for(tmp_path)
    cap = tmp_path / "c.jsonl"
    cap.write_text(json.dumps(ad(T0, name="WTEST0001")) + "\nnot json\n\n" + json.dumps(ad(T0 + 1, name="WTEST0001")) + "\n")
    stats = await replay(cap, engine, FakeParse(), speed="max")
    assert stats.ads == 2 and stats.bad_lines == 1


async def test_replay_at_1x_waits(tmp_path):
    engine = engine_for(tmp_path)
    cap = write_capture(tmp_path / "c.jsonl", [ad(T0, name="WTEST0001"), ad(T0 + 0.2, name="WTEST0001")])
    loop = asyncio.get_running_loop()
    start = loop.time()
    await replay(cap, engine, FakeParse(), speed="1x", drain=False)
    assert loop.time() - start >= 0.18
