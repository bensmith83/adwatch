"""The notifier interface (SPEC §4.11)."""

from __future__ import annotations


class Notifier:
    type = "base"

    async def send(self, alert: dict) -> None:
        """Deliver one alert (the masked view the page shows). Raise on failure."""
        raise NotImplementedError

    async def armed(self, armed: bool) -> None:
        """The armed state changed. Most notifiers don't care."""

    async def close(self) -> None:
        pass
