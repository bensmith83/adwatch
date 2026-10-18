"""Optional capture of the scanner's JSONL (SPEC §4.10 Capture).

Off by default. It is the only store of raw identifiers, for tuning and
replay only: one file per day (capture-YYYY-MM-DD.jsonl beside the configured
path), each capped in size, and only the last keep_days days kept.
"""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

log = logging.getLogger(__name__)


class CaptureWriter:
    def __init__(self, path: str, max_mb: float = 50, today=None, keep_days: int = 7):
        p = Path(path)
        self.dir = p.parent
        self.stem = p.stem
        self.suffix = p.suffix or ".jsonl"
        self.max_bytes = int(max_mb * 1024 * 1024)
        self.keep_days = keep_days
        self._today = today or (lambda: date.today().isoformat())
        self._day: str | None = None
        self._f = None
        self._size = 0
        self._full_logged = False
        self.dir.mkdir(parents=True, exist_ok=True)

    def _open(self, day: str) -> None:
        if self._f:
            self._f.close()
        path = self.dir / f"{self.stem}-{day}{self.suffix}"
        self._f = open(path, "a", buffering=1 << 16)
        self._size = path.stat().st_size
        self._day = day
        self._full_logged = False
        self._prune()

    def _prune(self) -> None:
        files = sorted(self.dir.glob(f"{self.stem}-????-??-??{self.suffix}"))
        for old in files[:-self.keep_days] if self.keep_days else []:
            old.unlink(missing_ok=True)

    def write(self, ad: dict) -> None:
        day = self._today()
        if day != self._day:
            self._open(day)
        line = json.dumps(ad, separators=(",", ":")) + "\n"
        if self._size + len(line) > self.max_bytes:
            if not self._full_logged:
                log.warning("capture file for %s reached its %d MB cap; not writing more today", day,
                            self.max_bytes // (1024 * 1024) or 1)
                self._full_logged = True
            return
        self._f.write(line)
        self._size += len(line)

    def close(self) -> None:
        if self._f:
            self._f.close()
            self._f = None
