"""Tests for the dashboard API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from adwatch.dashboard.app import create_app
from adwatch.dashboard.websocket import WebSocketManager
from adwatch.models import RawAdvertisement, Classification
from adwatch.registry import ParserRegistry
from adwatch.storage.base import Database
from adwatch.storage.migrations import run_migrations
from adwatch.storage.raw import RawStorage


@pytest.fixture
async def db(tmp_path):
    database = Database()
    await database.connect(str(tmp_path / "test.db"))
    await run_migrations(database)
    yield database
    await database.close()


@pytest.fixture
async def raw_storage(db):
    return RawStorage(db)


@pytest.fixture
def registry():
    return ParserRegistry()


@pytest.fixture
def ws_manager():
    return WebSocketManager()


@pytest.fixture
async def client(raw_storage, registry, ws_manager):
    app = create_app(
        raw_storage=raw_storage,
        classifier=None,
        registry=registry,
        ws_manager=ws_manager,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_overview_empty(client):
    resp = await client.get("/api/overview")
    assert resp.status_code == 200
    assert resp.json() == {}


@pytest.mark.asyncio
async def test_overview_with_data(client, raw_storage):
    classification = Classification(ad_type="apple_nearby", ad_category="phone", source="company_id")
    # Two different ads (different MACs = different signatures)
    ad1 = RawAdvertisement(
        timestamp="2025-01-15T10:30:00+00:00",
        mac_address="AA:BB:CC:DD:EE:01",
        address_type="random",
        manufacturer_data=None,
        service_data=None,
    )
    ad2 = RawAdvertisement(
        timestamp="2025-01-15T10:30:01+00:00",
        mac_address="AA:BB:CC:DD:EE:02",
        address_type="random",
        manufacturer_data=None,
        service_data=None,
    )
    await raw_storage.save(ad1, classification)
    await raw_storage.save(ad2, classification)

    resp = await client.get("/api/overview")
    assert resp.status_code == 200
    data = resp.json()
    # Overview now groups by ad_type, not ad_category
    assert "apple_nearby" in data


@pytest.mark.asyncio
async def test_feed_empty(client):
    resp = await client.get("/api/feed")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_feed_returns_recent(client, raw_storage):
    ad = RawAdvertisement(
        timestamp="2025-01-15T10:30:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        manufacturer_data=None,
        service_data=None,
        rssi=-62,
    )
    await raw_storage.save(ad)

    resp = await client.get("/api/feed?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["mac_address"] == "AA:BB:CC:DD:EE:FF"


@pytest.mark.asyncio
async def test_feed_respects_limit(client, raw_storage):
    for i in range(5):
        ad = RawAdvertisement(
            timestamp=f"2025-01-15T10:30:0{i}+00:00",
            mac_address=f"AA:BB:CC:DD:EE:{i:02X}",
            address_type="random",
            manufacturer_data=None,
            service_data=None,
        )
        await raw_storage.save(ad)

    resp = await client.get("/api/feed?limit=3")
    assert resp.status_code == 200
    assert len(resp.json()) == 3


@pytest.mark.asyncio
async def test_raw_query_no_filters(client, raw_storage):
    ad = RawAdvertisement(
        timestamp="2025-01-15T10:30:00+00:00",
        mac_address="11:22:33:44:55:66",
        address_type="random",
        manufacturer_data=None,
        service_data=None,
    )
    await raw_storage.save(ad)

    resp = await client.get("/api/raw")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1


@pytest.mark.asyncio
async def test_raw_query_filter_by_mac(client, raw_storage):
    for mac in ["AA:BB:CC:DD:EE:01", "AA:BB:CC:DD:EE:02"]:
        ad = RawAdvertisement(
            timestamp="2025-01-15T10:30:00+00:00",
            mac_address=mac,
            address_type="random",
            manufacturer_data=None,
            service_data=None,
        )
        await raw_storage.save(ad)

    resp = await client.get("/api/raw?mac=AA:BB:CC:DD:EE:01")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["mac_address"] == "AA:BB:CC:DD:EE:01"


@pytest.mark.asyncio
async def test_raw_query_filter_by_type(client, raw_storage):
    # Use different ads (different MACs) to get distinct signatures
    ad1 = RawAdvertisement(
        timestamp="2025-01-15T10:30:00+00:00",
        mac_address="AA:BB:CC:DD:EE:01",
        address_type="random",
        manufacturer_data=b"\x4c\x00\x01",
        service_data=None,
    )
    ad2 = RawAdvertisement(
        timestamp="2025-01-15T10:30:01+00:00",
        mac_address="AA:BB:CC:DD:EE:02",
        address_type="random",
        manufacturer_data=None,
        service_data=None,
        local_name="TP357",
    )
    cls1 = Classification(ad_type="apple_nearby", ad_category="phone", source="company_id")
    cls2 = Classification(ad_type="thermopro", ad_category="sensor", source="local_name")
    await raw_storage.save(ad1, cls1)
    await raw_storage.save(ad2, cls2)

    resp = await client.get("/api/raw?type=thermopro")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["ad_type"] == "thermopro"


@pytest.mark.asyncio
async def test_plugins_empty_registry(client):
    resp = await client.get("/api/plugins")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_plugins_ui_empty(client):
    resp = await client.get("/api/plugins/ui")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_websocket_manager_connect_disconnect():
    manager = WebSocketManager()

    class FakeWS:
        def __init__(self):
            self.accepted = False
            self.messages = []
        async def accept(self):
            self.accepted = True
        async def send_json(self, data):
            self.messages.append(data)

    ws = FakeWS()
    await manager.connect(ws)
    assert ws.accepted
    assert len(manager._connections) == 1

    await manager.disconnect(ws)
    assert len(manager._connections) == 0


@pytest.mark.asyncio
async def test_websocket_manager_emit():
    manager = WebSocketManager()

    class FakeWS:
        def __init__(self):
            self.messages = []
        async def accept(self):
            pass
        async def send_json(self, data):
            self.messages.append(data)

    ws1, ws2 = FakeWS(), FakeWS()
    await manager.connect(ws1)
    await manager.connect(ws2)

    await manager.emit("sighting", {"mac": "AA:BB"})

    assert len(ws1.messages) == 1
    assert ws1.messages[0]["type"] == "sighting"
    assert ws1.messages[0]["data"]["mac"] == "AA:BB"
    assert len(ws2.messages) == 1
