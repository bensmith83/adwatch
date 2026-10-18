"""Shared bits for the HTTP notifiers."""

from __future__ import annotations

import aiohttp

from .base import Notifier

TIMEOUT = aiohttp.ClientTimeout(total=10)


class HttpNotifier(Notifier):
    def __init__(self, url: str | None):
        if not url:
            raise ValueError(f"{self.type} notifier needs a url")
        self.url = url
        self._session: aiohttp.ClientSession | None = None

    def session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=TIMEOUT)
        return self._session

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()
