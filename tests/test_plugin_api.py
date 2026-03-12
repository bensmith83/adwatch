"""Tests for plugin management API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from adwatch.dashboard.app import create_app
from adwatch.dashboard.websocket import WebSocketManager
from adwatch.registry import ParserRegistry, register_parser
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
    reg = ParserRegistry()

    @register_parser(
        name="test_core",
        local_name_pattern=r"^CORE",
        description="A core parser",
        version="2.0.0",
        core=True,
        registry=reg,
    )
    class CoreParser:
        def parse(self, raw):
            return None

    @register_parser(
        name="test_plugin",
        local_name_pattern=r"^PLUG",
        description="A plugin parser",
        version="1.0.0",
        core=False,
        registry=reg,
    )
    class PluginParser:
        def parse(self, raw):
            return None

    return reg


@pytest.fixture
def ws_manager():
    return WebSocketManager()


@pytest.fixture
async def client(raw_storage, registry, ws_manager, db):
    app = create_app(
        raw_storage=raw_storage,
        classifier=None,
        registry=registry,
        ws_manager=ws_manager,
        db=db,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestPluginAPI:
    @pytest.mark.asyncio
    async def test_get_plugins_returns_all_with_fields(self, client):
        """GET /api/plugins should return list with name, description, version, core, enabled."""
        resp = await client.get("/api/plugins")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

        by_name = {p["name"]: p for p in data}
        core = by_name["test_core"]
        assert core["description"] == "A core parser"
        assert core["version"] == "2.0.0"
        assert core["core"] is True
        assert "enabled" in core
        assert core["enabled"] is True

        plugin = by_name["test_plugin"]
        assert plugin["core"] is False
        assert plugin["enabled"] is True

    @pytest.mark.asyncio
    async def test_toggle_plugin_disables(self, client):
        """PUT /api/plugins/{name}/toggle should toggle enabled state."""
        resp = await client.put("/api/plugins/test_plugin/toggle")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "test_plugin"
        assert data["enabled"] is False

    @pytest.mark.asyncio
    async def test_toggle_nonexistent_returns_404(self, client):
        """PUT /api/plugins/{nonexistent}/toggle should return 404."""
        resp = await client.put("/api/plugins/nonexistent/toggle")
        assert resp.status_code == 404
