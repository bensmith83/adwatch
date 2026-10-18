"""Learning (SPEC §4.8): for the first learning_days nothing is pushed; then
the neighbours' fixed things and the regulars are auto-baselined."""

from __future__ import annotations

from datetime import tzinfo

from .model import Unit, Visit
from .rules import LOW_MOBILITY
from .timeutil import local_day

DAY_S = 86400.0
REGULAR_DAYS = 3


class Learning:
    def __init__(self, days: float, state, now: float):
        self.days = days
        self.state = state
        if state.get("learning_started") is None:
            state.set_state("learning_started", now)
            state.set_state("learning_done", False)

    @property
    def started(self) -> float:
        return self.state.get("learning_started")

    @property
    def ends(self) -> float:
        return self.started + self.days * DAY_S

    @property
    def done(self) -> bool:
        return bool(self.state.get("learning_done", False))

    def active(self, now: float) -> bool:
        return not self.done and now < self.ends

    def due(self, now: float) -> bool:
        return not self.done and now >= self.ends

    def finish(self, units: dict[int, Unit], history: dict[int, list[Visit]], open_visits: dict[int, Visit],
               rssi_floor: int, tz: tzinfo) -> set[int]:
        """End learning: baseline fixed/movable units that had a near visit
        and any unit seen on REGULAR_DAYS or more distinct days."""
        chosen = set()
        for uid, u in units.items():
            visits = list(history.get(uid, []))
            if uid in open_visits:
                visits.append(open_visits[uid])
            near = any(v.max_rssi >= rssi_floor for v in visits)
            days = {local_day(v.start, tz) for v in visits}
            if (u.mobility in LOW_MOBILITY and near) or len(days) >= REGULAR_DAYS:
                u.baseline = True
                chosen.add(uid)
        self.state.set_state("learning_done", True)
        return chosen

    def relearn(self, units: dict[int, Unit], now: float) -> None:
        for u in units.values():
            u.baseline = False
        self.state.set_state("learning_started", now)
        self.state.set_state("learning_done", False)

    def status(self, now: float) -> dict:
        return {"active": self.active(now), "started": self.started, "ends": self.ends, "done": self.done}
