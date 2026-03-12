"""SQLite connection management via aiosqlite."""

import sqlite3

import aiosqlite


class Database:
    """Async SQLite database wrapper."""

    def __init__(self):
        self._conn: aiosqlite.Connection | None = None

    async def connect(self, db_path: str) -> None:
        self._conn = await aiosqlite.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        await self._conn.execute("PRAGMA foreign_keys = ON")
        await self._conn.execute("PRAGMA busy_timeout = 5000")
        if db_path != ":memory:":
            await self._conn.execute("PRAGMA journal_mode = WAL")

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def execute(self, sql: str, params=None) -> None:
        await self._conn.execute(sql, params or ())
        await self._conn.commit()

    async def fetchall(self, sql: str, params=None) -> list[dict]:
        cursor = await self._conn.execute(sql, params or ())
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def fetchone(self, sql: str, params=None) -> dict | None:
        cursor = await self._conn.execute(sql, params or ())
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def commit(self) -> None:
        await self._conn.commit()

    async def rollback(self) -> None:
        await self._conn.rollback()
