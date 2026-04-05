"""Persist and retrieve AI-generated insights."""

import time

from adwatch.storage.base import Database

INTERVAL_SECONDS = {
    "1h": 3600,
    "4h": 4 * 3600,
    "12h": 12 * 3600,
    "daily": 24 * 3600,
}


class InsightsStorage:
    def __init__(self, db: Database):
        self._db = db

    async def save(
        self,
        summary_payload: str,
        insight_text: str,
        provider: str,
        model: str | None,
        token_count: int | None,
    ) -> None:
        await self._db.execute(
            "INSERT INTO insights (generated_at, summary_payload, insight_text, provider, model, token_count) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (time.time(), summary_payload, insight_text, provider, model, token_count),
        )

    async def get_latest(self) -> dict | None:
        return await self._db.fetchone(
            "SELECT * FROM insights ORDER BY generated_at DESC LIMIT 1"
        )

    async def get_history(self, limit: int = 10) -> list[dict]:
        return await self._db.fetchall(
            "SELECT * FROM insights ORDER BY generated_at DESC LIMIT ?",
            (limit,),
        )

    async def should_refresh(self, interval: str) -> bool:
        if interval == "manual":
            return False

        seconds = INTERVAL_SECONDS.get(interval)
        if seconds is None:
            return False

        latest = await self.get_latest()
        if latest is None:
            return True

        return (time.time() - latest["generated_at"]) >= seconds
