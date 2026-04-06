"""Tests for Insights API endpoints."""

import json
import time
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from adwatch.storage.base import Database
from adwatch.storage.migrations import run_migrations
from adwatch.insights.storage import InsightsStorage
from adwatch.insights.aggregator import InsightsAggregator
from adwatch.insights.ai_client import InsightResult
from adwatch.dashboard.routers.insights import create_insights_router

from fastapi import FastAPI


@pytest.fixture
async def db():
    d = Database()
    await d.connect(":memory:")
    await run_migrations(d)
    yield d
    await d.close()


@pytest.fixture
async def app(db):
    insights_storage = InsightsStorage(db)
    aggregator = InsightsAggregator(db)
    a = FastAPI()
    a.include_router(create_insights_router(insights_storage, aggregator))
    return a


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestInsightsConfig:
    async def test_get_config(self, client):
        with patch("adwatch.dashboard.routers.insights.config") as mock_config:
            mock_config.AI_API_KEY = "sk-test"
            mock_config.AI_PROVIDER = "claude"
            mock_config.INSIGHTS_INTERVAL = "daily"
            mock_config.INSIGHTS_TIME = "08:00"
            resp = await client.get("/api/insights/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider"] == "claude"
        assert data["has_api_key"] is True
        assert "sk-test" not in json.dumps(data)  # key not exposed

    async def test_config_no_key(self, client):
        with patch("adwatch.dashboard.routers.insights.config") as mock_config:
            mock_config.AI_API_KEY = ""
            mock_config.AI_PROVIDER = "claude"
            mock_config.INSIGHTS_INTERVAL = "daily"
            mock_config.INSIGHTS_TIME = "08:00"
            resp = await client.get("/api/insights/config")
        data = resp.json()
        assert data["has_api_key"] is False


class TestInsightsLatest:
    async def test_latest_empty(self, client):
        resp = await client.get("/api/insights/latest")
        assert resp.status_code == 200
        data = resp.json()
        assert data["insight"] is None

    async def test_latest_with_data(self, db, client):
        storage = InsightsStorage(db)
        await storage.save('{"test": true}', "## Analysis\nGreat stuff.", "claude", "claude-sonnet-4-20250514", 500)
        resp = await client.get("/api/insights/latest")
        data = resp.json()
        assert data["insight"] is not None
        assert "Analysis" in data["insight"]["insight_text"]


class TestInsightsGenerate:
    async def test_generate_no_key(self, client):
        with patch("adwatch.dashboard.routers.insights.config") as mock_config:
            mock_config.AI_API_KEY = ""
            mock_config.AI_PROVIDER = "claude"
            resp = await client.post("/api/insights/generate")
        assert resp.status_code == 400
        assert "API key" in resp.json()["detail"]

    async def test_generate_success(self, client):
        mock_result = InsightResult(
            text="## Environment\nThis is a home.",
            model="claude-sonnet-4-20250514",
            token_count=400,
        )
        with patch("adwatch.dashboard.routers.insights.config") as mock_config, \
             patch("adwatch.dashboard.routers.insights.InsightsClient") as MockClient:
            mock_config.AI_API_KEY = "sk-test"
            mock_config.AI_PROVIDER = "claude"
            mock_instance = AsyncMock()
            mock_instance.generate = AsyncMock(return_value=mock_result)
            MockClient.return_value = mock_instance

            resp = await client.post("/api/insights/generate")

        assert resp.status_code == 200
        data = resp.json()
        assert "Environment" in data["insight_text"]
        assert data["provider"] == "claude"


class TestInsightsHistory:
    async def test_history_empty(self, client):
        resp = await client.get("/api/insights/history")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_history_with_data(self, db, client):
        storage = InsightsStorage(db)
        await storage.save("p1", "First", "claude", "m1", 100)
        await storage.save("p2", "Second", "openai", "m2", 200)
        resp = await client.get("/api/insights/history")
        data = resp.json()
        assert len(data) == 2
        assert data[0]["insight_text"] == "Second"


class TestInsightsPayloadPreview:
    async def test_payload_preview(self, client):
        resp = await client.get("/api/insights/payload-preview")
        assert resp.status_code == 200
        data = resp.json()
        assert "totals" in data
        assert "scan_period" in data
