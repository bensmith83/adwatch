"""Tests for Database PRAGMA hardening — WAL, foreign keys, busy timeout."""

import pytest
import pytest_asyncio

from adwatch.storage.base import Database
from adwatch.storage.migrations import run_migrations


@pytest_asyncio.fixture
async def db():
    """In-memory SQLite database, migrated and ready."""
    database = Database()
    await database.connect(":memory:")
    await run_migrations(database)
    yield database
    await database.close()


class TestDatabasePragmas:
    """After connect(), Database should set hardening PRAGMAs."""

    @pytest.mark.asyncio
    async def test_foreign_keys_enabled(self, db):
        """PRAGMA foreign_keys should be ON (1) after connect()."""
        row = await db.fetchone("PRAGMA foreign_keys")
        assert row["foreign_keys"] == 1

    @pytest.mark.asyncio
    async def test_journal_mode_wal(self):
        """PRAGMA journal_mode should be 'wal' after connect().

        Note: WAL is not supported on :memory: databases, so we skip this
        or accept 'memory' mode. Instead, test that the PRAGMA is issued
        by checking a real temp file.
        """
        import tempfile
        import os

        db = Database()
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        try:
            await db.connect(tmp.name)
            await run_migrations(db)
            row = await db.fetchone("PRAGMA journal_mode")
            assert row["journal_mode"] == "wal"
            await db.close()
        finally:
            os.unlink(tmp.name)
            # Clean up WAL/SHM files
            for ext in ("-wal", "-shm"):
                try:
                    os.unlink(tmp.name + ext)
                except FileNotFoundError:
                    pass

    @pytest.mark.asyncio
    async def test_busy_timeout_set(self, db):
        """PRAGMA busy_timeout should be 5000ms after connect()."""
        row = await db.fetchone("PRAGMA busy_timeout")
        assert row["timeout"] == 5000
