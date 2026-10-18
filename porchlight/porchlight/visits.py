"""Visits: unbroken presences of a unit (SPEC §4.5).

Sightings with gaps of at most gap_s belong to one visit. Open visits live in
memory and are written when they close, plus a checkpoint every CHECKPOINT_S.
Closed visits are kept per unit as the history the rules read.
"""

from __future__ import annotations

from .model import Visit
from .store import Snapshot, Store

CHECKPOINT_S = 60.0


class VisitTracker:
    def __init__(self, gap_s: float, rssi_floor: int, store: Store, next_id: int = 1):
        self.gap = gap_s
        self.floor = rssi_floor
        self.store = store
        self.open: dict[int, Visit] = {}
        self.history: dict[int, list[Visit]] = {}
        self._next_id = next_id
        self._last_checkpoint: float | None = None

    def restore(self, snap: Snapshot, now: float) -> None:
        """Rebuild from storage: visits that ended within the gap reopen."""
        self._next_id = max(self._next_id, snap.next_ids.get("visit", 1))
        for v in snap.visits:
            if now - v.end <= self.gap and v.unit_id not in self.open:
                self.open[v.unit_id] = v
            else:
                self.history.setdefault(v.unit_id, []).append(v)

    def is_near(self, v: Visit) -> bool:
        return v.max_rssi >= self.floor

    def sight(self, unit_id: int, t: float, rssi: int) -> tuple[Visit, Visit | None]:
        """Returns the current visit, and the previous one if this sighting
        closed it."""
        closed = None
        v = self.open.get(unit_id)
        if v is not None and t - v.end > self.gap:
            closed = self._close(v)
            v = None
        if v is None:
            v = Visit(id=self._next_id, unit_id=unit_id, start=t, end=t, n=0, max_rssi=rssi, sum_rssi=0.0)
            self._next_id += 1
            self.open[unit_id] = v
        v.end = max(v.end, t)
        v.n += 1
        v.max_rssi = max(v.max_rssi, rssi)
        v.sum_rssi += rssi
        v.last_rssi = rssi
        return v, closed

    def sweep(self, now: float) -> list[Visit]:
        return [self._close(v) for v in list(self.open.values()) if now - v.end > self.gap]

    def checkpoint(self, now: float, force: bool = False) -> bool:
        if not force and self._last_checkpoint is not None and now - self._last_checkpoint < CHECKPOINT_S:
            return False
        for v in self.open.values():
            self.store.put_visit(v)
        self._last_checkpoint = now
        return True

    def merge(self, keep: int, gone: int) -> None:
        for v in self.history.pop(gone, []):
            v.unit_id = keep
            self.history.setdefault(keep, []).append(v)
        if keep in self.history:
            self.history[keep].sort(key=lambda v: v.start)
        b = self.open.pop(gone, None)
        if b is None:
            return
        a = self.open.get(keep)
        if a is None:
            b.unit_id = keep
            self.open[keep] = b
            self.store.put_visit(b)
            return
        a.start, a.end = min(a.start, b.start), max(a.end, b.end)
        a.n += b.n
        a.max_rssi = max(a.max_rssi, b.max_rssi)
        a.sum_rssi += b.sum_rssi
        self.store.delete_visit(b.id)
        self.store.put_visit(a)

    def remove(self, unit_ids) -> None:
        for uid in unit_ids:
            self.open.pop(uid, None)
            self.history.pop(uid, None)

    def prune(self, before: float) -> None:
        for uid in list(self.history):
            kept = [v for v in self.history[uid] if v.end >= before]
            if kept:
                self.history[uid] = kept
            else:
                del self.history[uid]

    def _close(self, v: Visit) -> Visit:
        del self.open[v.unit_id]
        self.history.setdefault(v.unit_id, []).append(v)
        self.store.put_visit(v)
        return v
