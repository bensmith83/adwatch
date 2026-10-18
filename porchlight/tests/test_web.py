import pytest
from aiohttp.test_utils import TestClient, TestServer

from fakes import T0, TABLE, TZ, ad, watch
from porchlight.config import Config
from porchlight.engine import Engine
from porchlight.store import Store
from porchlight.web.server import make_app


def make_engine(tmp_path, **arming):
    cfg = Config()
    cfg.learning.learning_days = 0
    for k, v in arming.items():
        setattr(cfg.arming, k, v)
    return cfg, Engine(cfg, TABLE, Store(tmp_path / "p.db"), now=T0, tz=TZ)


async def client_for(engine, token=""):
    app = make_app(engine, token=token)
    client = TestClient(TestServer(app))
    await client.start_server()
    return client


def linger(engine, minutes=11):
    t = T0
    while t <= T0 + minutes * 60:
        engine.ingest(ad(t), watch())
        engine.tick(t)
        t += 10


@pytest.fixture
async def setup(tmp_path):
    cfg, engine = make_engine(tmp_path)
    client = await client_for(engine)
    yield engine, client
    await client.close()
    engine.store.close()


async def test_the_page_is_served_and_says_what_it_cannot_see(setup):
    _, client = setup
    r = await client.get("/")
    assert r.status == 200
    html = await r.text()
    assert "can't see phones" in html and "doesn't look for unwanted trackers" in html
    r = await client.get("/app.js")
    assert r.status == 200
    assert '"Parser commit"' in await r.text()


async def test_state(setup):
    engine, client = setup
    linger(engine)
    r = await client.get("/api/state")
    assert r.status == 200
    s = await r.json()
    assert s["armed"]["mode"] == "manual"
    assert [a["rule"] for a in s["alerts"]] == ["R1"]
    assert "TEST0001" not in await r.text()


async def test_arm_toggle(setup):
    engine, client = setup
    r = await client.post("/api/arm", json={"armed": True})
    assert r.status == 200
    assert (await r.json())["armed"]["armed"] is True
    assert engine.arming.armed is True


async def test_ack_and_label_from_the_alert(setup):
    engine, client = setup
    linger(engine)
    (a,) = engine.state()["alerts"]
    r = await client.post(f"/api/alerts/{a['id']}/ack", json={"label": "known", "name": "Postie"})
    assert r.status == 200
    assert engine.units.units[a["unit_id"]].label == "known"
    assert (await (await client.get("/api/state")).json())["alerts"] == []


async def test_label_a_unit_and_reject_bad_labels(setup):
    engine, client = setup
    engine.ingest(ad(T0), watch())
    (u,) = engine.units.units.values()
    r = await client.post(f"/api/units/{u.id}/label", json={"label": "household", "name": "My watch"})
    assert r.status == 200 and u.label == "household"
    r = await client.post(f"/api/units/{u.id}/label", json={"label": None})
    assert r.status == 200 and u.label is None
    r = await client.post(f"/api/units/{u.id}/label", json={"label": "pal"})
    assert r.status == 400
    r = await client.post("/api/units/999/label", json={"label": "known"})
    assert r.status == 404


async def test_devices_search_and_history(setup):
    engine, client = setup
    linger(engine, minutes=1)
    r = await client.get("/api/units", params={"q": "watch"})
    (u,) = await r.json()
    assert u["product"] == "Watch"
    assert await (await client.get("/api/units", params={"q": "toaster"})).json() == []
    d = await (await client.get(f"/api/units/{u['id']}")).json()
    assert len(d["visits"]) == 1


async def test_relearn(setup):
    engine, client = setup
    r = await client.post("/api/relearn", json={})
    assert r.status == 200
    assert engine.learning.started == engine.now and not engine.learning.done


async def test_posts_must_be_json(setup):
    _, client = setup
    r = await client.post("/api/arm", data="armed=true", headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert r.status == 415


async def test_token_is_required_when_set(tmp_path):
    _, engine = make_engine(tmp_path)
    client = await client_for(engine, token="s3cret")
    try:
        assert (await client.get("/api/state")).status == 401
        assert (await client.get("/")).status == 401
        assert (await client.get("/api/state", headers={"Authorization": "Bearer nope"})).status == 401
        assert (await client.get("/api/state", headers={"Authorization": "Bearer s3cret"})).status == 200
        r = await client.get("/?token=s3cret", allow_redirects=False)
        assert r.status in (200, 302, 303)
        assert "porchlight_token" in r.cookies
        assert (await client.get("/api/state")).status == 200, "the cookie now authenticates"
        assert (await client.post("/api/arm", json={"armed": True})).status == 200
    finally:
        await client.close()
        engine.store.close()
