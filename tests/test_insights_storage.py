"""Tests for InsightsStorage."""

import time

import pytest

from adwatch.storage.base import Database
from adwatch.storage.migrations import run_migrations
from adwatch.insights.storage import InsightsStorage


@pytest.fixture
async def db():
    d = Database()
    await d.connect(":memory:")
    await run_migrations(d)
    yield d
    await d.close()


@pytest.fixture
async def storage(db):
    return InsightsStorage(db)


class TestInsightsStorage:
    async def test_save_and_get_latest(self, storage):
        await storage.save(
            summary_payload='{"totals": {"total_ads": 100}}',
            insight_text="Test insight",
            provider="claude",
            model="claude-sonnet-4-20250514",
            token_count=500,
        )
        latest = await storage.get_latest()
        assert latest is not None
        assert latest["insight_text"] == "Test insight"
        assert latest["provider"] == "claude"
        assert latest["model"] == "claude-sonnet-4-20250514"
        assert latest["token_count"] == 500

    async def test_get_latest_returns_none_when_empty(self, storage):
        latest = await storage.get_latest()
        assert latest is None

    async def test_get_latest_returns_most_recent(self, storage):
        await storage.save("p1", "First insight", "claude", "m1", 100)
        await storage.save("p2", "Second insight", "claude", "m2", 200)
        latest = await storage.get_latest()
        assert latest["insight_text"] == "Second insight"

    async def test_get_history(self, storage):
        await storage.save("p1", "First", "claude", "m1", 100)
        await storage.save("p2", "Second", "openai", "m2", 200)
        await storage.save("p3", "Third", "claude", "m3", 300)
        history = await storage.get_history(limit=2)
        assert len(history) == 2
        assert history[0]["insight_text"] == "Third"
        assert history[1]["insight_text"] == "Second"

    async def test_get_history_default_limit(self, storage):
        for i in range(15):
            await storage.save(f"p{i}", f"Insight {i}", "claude", "m", 10)
        history = await storage.get_history()
        assert len(history) == 10

    async def test_should_refresh_true_when_no_insights(self, storage):
        assert await storage.should_refresh("daily") is True

    async def test_should_refresh_false_when_recent(self, storage):
        await storage.save("p", "text", "claude", "m", 10)
        assert await storage.should_refresh("daily") is False

    async def test_should_refresh_manual_always_false(self, storage):
        """Manual mode never auto-refreshes."""
        assert await storage.should_refresh("manual") is False

    async def test_should_refresh_respects_interval(self, db):
        """Should refresh when last insight is older than interval."""
        storage = InsightsStorage(db)
        # Insert an old insight (25 hours ago)
        old_time = time.time() - 25 * 3600
        await db.execute(
            "INSERT INTO insights (generated_at, summary_payload, insight_text, provider, model, token_count) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (old_time, "p", "old", "claude", "m", 10),
        )
        assert await storage.should_refresh("daily") is True
        assert await storage.should_refresh("4h") is True

    async def test_should_refresh_4h_interval(self, db):
        """4h interval: refresh after 4 hours."""
        storage = InsightsStorage(db)
        recent_time = time.time() - 2 * 3600  # 2 hours ago
        await db.execute(
            "INSERT INTO insights (generated_at, summary_payload, insight_text, provider, model, token_count) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (recent_time, "p", "recent", "claude", "m", 10),
        )
        assert await storage.should_refresh("4h") is False

    async def test_save_stores_generated_at(self, storage):
        before = time.time()
        await storage.save("p", "text", "claude", "m", 10)
        after = time.time()
        latest = await storage.get_latest()
        assert before <= latest["generated_at"] <= after
