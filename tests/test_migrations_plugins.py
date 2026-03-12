"""Tests for plugin table creation during migrations."""

import pytest

from adwatch.storage.base import Database
from adwatch.storage.migrations import run_migrations
from adwatch.registry import ParserRegistry


class TestPluginMigrations:
    @pytest.mark.asyncio
    async def test_creates_plugin_tables(self, tmp_path):
        db = Database()
        await db.connect(str(tmp_path / "test.db"))

        registry = ParserRegistry()

        class FakeParser:
            def parse(self, raw):
                return None
            def storage_schema(self):
                return "CREATE TABLE IF NOT EXISTS fake_sightings (id INTEGER PRIMARY KEY, value TEXT)"

        registry.register(
            name="fake", instance=FakeParser(),
            description="test", version="1.0.0", core=False,
        )

        await run_migrations(db, registry=registry)

        rows = await db.fetchall(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='fake_sightings'"
        )
        assert len(rows) == 1
        await db.close()

    @pytest.mark.asyncio
    async def test_skips_plugins_without_schema(self, tmp_path):
        db = Database()
        await db.connect(str(tmp_path / "test.db"))

        registry = ParserRegistry()

        class NoSchemaParser:
            def parse(self, raw):
                return None

        registry.register(
            name="noschema", instance=NoSchemaParser(),
            description="test", version="1.0.0", core=False,
        )

        await run_migrations(db, registry=registry)
        # Should not raise
        await db.close()

    @pytest.mark.asyncio
    async def test_works_without_registry(self, tmp_path):
        """Backwards compatible — no registry means just core tables."""
        db = Database()
        await db.connect(str(tmp_path / "test.db"))

        await run_migrations(db)

        rows = await db.fetchall(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='raw_advertisements'"
        )
        assert len(rows) == 1
        await db.close()
