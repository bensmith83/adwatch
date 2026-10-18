"""`webhook`: POSTs the alert JSON (the masked view the page shows)."""

from __future__ import annotations

from ..config import Notify
from .http import HttpNotifier


class WebhookNotifier(HttpNotifier):
    type = "webhook"

    def __init__(self, cfg: Notify):
        super().__init__(cfg.options.get("url"))
        self.headers = dict(cfg.options.get("headers") or {})

    async def send(self, alert: dict) -> None:
        async with self.session().post(self.url, json=alert, headers=self.headers) as r:
            r.raise_for_status()
