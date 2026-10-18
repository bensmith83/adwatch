"""`ntfy`: an HTTP POST to the topic URL, with an optional access token."""

from __future__ import annotations

from ..config import Notify
from .http import HttpNotifier

PRIORITY = {"alert": "high", "warn": "default"}
TAGS = {"alert": "rotating_light", "warn": "warning"}


class NtfyNotifier(HttpNotifier):
    type = "ntfy"

    def __init__(self, cfg: Notify):
        super().__init__(cfg.options.get("url"))
        self.token = cfg.options.get("token") or ""

    async def send(self, alert: dict) -> None:
        headers = {"Title": alert.get("title") or alert["rule"],
                   "Priority": PRIORITY.get(alert["severity"], "default"),
                   "Tags": TAGS.get(alert["severity"], "")}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        async with self.session().post(self.url, data=(alert.get("message") or "").encode(), headers=headers) as r:
            r.raise_for_status()
