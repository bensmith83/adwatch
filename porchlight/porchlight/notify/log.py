"""`log`: one line per alert on stdout, which goes to journald."""

from __future__ import annotations

import logging

from ..config import Notify
from .base import Notifier

log = logging.getLogger("porchlight.alerts")


class LogNotifier(Notifier):
    type = "log"

    def __init__(self, cfg: Notify):
        self.cfg = cfg

    async def send(self, alert: dict) -> None:
        level = logging.WARNING if alert["severity"] == "alert" else logging.INFO
        log.log(level, "%s %s %s: %s", alert["severity"].upper(), alert["rule"], alert.get("title", ""),
                alert.get("message", ""))

    async def armed(self, armed: bool) -> None:
        log.info("house %s", "armed" if armed else "disarmed")
