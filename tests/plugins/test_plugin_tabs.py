"""Tests for plugin UI tabs and API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from adwatch.plugins.tile import TileParser
from adwatch.plugins.smarttag import SmartTagParser
from adwatch.plugins.matter import MatterParser
from adwatch.storage.base import Database
from adwatch.storage.migrations import run_migrations
from adwatch.storage.raw import RawStorage
from adwatch.models import RawAdvertisement, Classification


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


class TestTileUI:
    def test_ui_config_returns_tab(self):
        parser = TileParser()
        cfg = parser.ui_config()
        assert cfg is not None
        assert cfg.tab_name == "Tile"

    @pytest.mark.asyncio
    async def test_api_recent(self, db, raw_storage):
        parser = TileParser()
        router = parser.api_router(db)
        assert router is not None

        app = FastAPI()
        app.include_router(router)
        transport = ASGITransport(app=app)

        # Insert a tile sighting
        ad = RawAdvertisement(
            timestamp="2025-01-15T10:30:00+00:00",
            mac_address="TI:LE:00:00:00:01",
            address_type="random",
            manufacturer_data=None,
            service_data=None,
        )
        await raw_storage.save(ad, Classification(ad_type="tile", ad_category="tracker", source="service_uuid"), parsed_by=["tile"])

        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/recent")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            assert data[0]["mac_address"] == "TI:LE:00:00:00:01"


class TestSmartTagUI:
    def test_ui_config_returns_tab(self):
        parser = SmartTagParser()
        cfg = parser.ui_config()
        assert cfg is not None
        assert cfg.tab_name == "SmartTag"


class TestMatterUI:
    def test_ui_config_returns_tab(self):
        parser = MatterParser()
        cfg = parser.ui_config()
        assert cfg is not None
        assert cfg.tab_name == "Matter"


# --- Widget type tests ---

from adwatch.plugins.thermopro import ThermoProParser
from adwatch.models import WidgetConfig
from adwatch.registry import ParserRegistry


class TestThermoProWidgetType:
    """ThermoPro should use sensor_card widget type instead of device_card."""

    def test_widget_type_is_sensor_card(self):
        parser = ThermoProParser()
        cfg = parser.ui_config()
        widget_types = [w.widget_type for w in cfg.widgets]
        assert "sensor_card" in widget_types
        assert "device_card" not in widget_types


class TestWidgetRenderHints:
    """WidgetConfig should support render_hints dict."""

    def test_widget_config_accepts_render_hints(self):
        w = WidgetConfig(
            widget_type="sensor_card",
            title="Test",
            data_endpoint="/api/test",
            render_hints={"primary_field": "temperature_c"},
        )
        assert w.render_hints == {"primary_field": "temperature_c"}

    def test_widget_config_render_hints_defaults_empty(self):
        w = WidgetConfig(
            widget_type="sensor_card",
            title="Test",
            data_endpoint="/api/test",
        )
        assert w.render_hints == {}

    def test_thermopro_sensor_card_has_render_hints(self):
        parser = ThermoProParser()
        cfg = parser.ui_config()
        sensor_widgets = [w for w in cfg.widgets if w.widget_type == "sensor_card"]
        assert len(sensor_widgets) > 0
        hints = sensor_widgets[0].render_hints
        assert "primary_field" in hints
        assert "secondary_field" in hints
        assert "badge_fields" in hints


class TestPluginsUIEndpointWidgetTypes:
    """The /api/plugins/ui endpoint should return full widget configs."""

    @pytest.fixture
    def registry_with_thermopro(self):
        reg = ParserRegistry()
        parser = ThermoProParser()
        reg.register(
            name="thermopro",
            local_name_pattern=r"^TP\d{3}",
            description="ThermoPro sensors",
            version="1.0.0",
            core=False,
            instance=parser,
        )
        return reg

    @pytest.fixture
    async def ui_client(self, registry_with_thermopro, tmp_path):
        from adwatch.dashboard.routers.overview import create_overview_router
        from adwatch.storage.raw import RawStorage

        database = Database()
        await database.connect(str(tmp_path / "ui_test.db"))
        await run_migrations(database)
        raw_storage = RawStorage(database)

        router = create_overview_router(raw_storage, registry_with_thermopro)
        app = FastAPI()
        app.include_router(router)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
        await database.close()

    @pytest.mark.asyncio
    async def test_plugins_ui_returns_widget_type(self, ui_client):
        resp = await ui_client.get("/api/plugins/ui?all=true")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        # Every widget should have a widget_type field
        for plugin_cfg in data:
            for widget in plugin_cfg["widgets"]:
                assert "widget_type" in widget

    @pytest.mark.asyncio
    async def test_plugins_ui_sensor_card_has_render_hints(self, ui_client):
        resp = await ui_client.get("/api/plugins/ui?all=true")
        data = resp.json()
        # Find thermopro config
        thermo_cfg = [c for c in data if c["tab_name"] == "ThermoPro"][0]
        sensor_widgets = [w for w in thermo_cfg["widgets"] if w["widget_type"] == "sensor_card"]
        assert len(sensor_widgets) > 0
        hints = sensor_widgets[0]["render_hints"]
        assert "primary_field" in hints
        assert "secondary_field" in hints
        assert "badge_fields" in hints

    @pytest.mark.asyncio
    async def test_plugins_ui_includes_render_hints_key(self, ui_client):
        """Every widget in /api/plugins/ui should have render_hints."""
        resp = await ui_client.get("/api/plugins/ui?all=true")
        data = resp.json()
        for plugin_cfg in data:
            for widget in plugin_cfg["widgets"]:
                assert "render_hints" in widget


class TestDataTableWidgetRenderHints:
    """data_table widgets should have render_hints with 'columns' list."""

    def test_data_table_render_hints_has_columns(self):
        w = WidgetConfig(
            widget_type="data_table",
            title="Recent Sightings",
            data_endpoint="/api/test/recent",
            render_hints={"columns": ["timestamp", "mac_address", "rssi"]},
        )
        assert "columns" in w.render_hints
        assert isinstance(w.render_hints["columns"], list)


class TestDeviceCardWidgetRenderHints:
    """device_card widgets should have render_hints with 'fields' list."""

    def test_device_card_render_hints_has_fields(self):
        w = WidgetConfig(
            widget_type="device_card",
            title="Devices",
            data_endpoint="/api/test/devices",
            render_hints={"fields": ["name", "status"]},
        )
        assert "fields" in w.render_hints
        assert isinstance(w.render_hints["fields"], list)
