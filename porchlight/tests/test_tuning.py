"""M4 tuning helpers: the RSSI calibration trace and per-rule counts."""

import pytest
from aiohttp.test_utils import TestClient, TestServer

from fakes import T0, TABLE, TZ, ad, watch
from porchlight.config import Config
from porchlight.engine import Engine
from porchlight.store import Store
from porchlight.web.server import make_app


@pytest.fixture
def engine(tmp_path):
    cfg = Config()
    cfg.learning.learning_days = 0
    e = Engine(cfg, TABLE, Store(tmp_path / "p.db"), now=T0, tz=TZ)
    yield e
    e.store.close()


def test_rssi_trace_keeps_the_last_minute(engine):
    for i in range(90):
        engine.ingest(ad(T0 + i, rssi=-60 - i % 10), watch())
    (u,) = engine.units.units.values()
    tr = engine.rssi_trace(u.id)
    assert tr["floor"] == -80
    assert tr["rssi"] == -60 - 89 % 10
    assert all(t >= T0 + 89 - 60 for t, _ in tr["samples"])
    assert len(tr["samples"]) == 61
    assert tr["min"] == -69 and tr["max"] == -60
    assert tr["near"] is True
    assert tr["unit"]["product"] == "Watch"


def test_rssi_trace_for_a_unit_out_of_range(engine):
    engine.ingest(ad(T0), watch())
    (u,) = engine.units.units.values()
    engine.tick(T0 + 3600)
    tr = engine.rssi_trace(u.id)
    assert tr["rssi"] is None and tr["samples"] == []
    assert engine.rssi_trace(999) is None


def test_rule_counts_split_pushed_info_and_would_have(tmp_path):
    cfg = Config()
    cfg.learning.learning_days = 1
    e = Engine(cfg, TABLE, Store(tmp_path / "p.db"), now=T0, tz=TZ)
    t = T0
    while t <= T0 + 11 * 60:                       # during learning: a would-have R1
        e.ingest(ad(t), watch("TEST0001"))
        t += 10
    t = T0 + 2 * 86400
    while t <= T0 + 2 * 86400 + 11 * 60:           # after learning: a real R1
        e.ingest(ad(t, addr="40:00:00:00:00:02"), watch("TEST0002"))
        e.tick(t)
        t += 10
    counts = e.state()["rule_counts"]
    assert counts["R1"] == {"alert": 1, "warn": 0, "info": 0, "would_have": 1}
    assert counts["R2"] == {"alert": 0, "warn": 0, "info": 0, "would_have": 0}
    e.store.close()


async def test_rssi_route(engine):
    engine.ingest(ad(T0, rssi=-71), watch())
    (u,) = engine.units.units.values()
    client = TestClient(TestServer(make_app(engine)))
    await client.start_server()
    try:
        r = await client.get(f"/api/units/{u.id}/rssi")
        assert r.status == 200 and (await r.json())["rssi"] == -71
        assert (await client.get("/api/units/999/rssi")).status == 404
    finally:
        await client.close()
