"""Arming (SPEC §4.7): always, manual, schedule or presence.

In every mode a manual override from the page lasts until the next automatic
transition: a schedule edge or a presence change. `state` is the persisted
state table (get / set_state), so the manual toggle, the override and the
last household sighting survive restarts.
"""

from __future__ import annotations

from datetime import tzinfo

from .config import Arming as ArmingConfig
from .timeutil import Window, in_windows


class Arming:
    def __init__(self, cfg: ArmingConfig, tz: tzinfo, state, now: float):
        self.cfg = cfg
        self.mode = cfg.mode
        self.tz = tz
        self.state = state
        self.windows = [Window.parse(w) for w in cfg.schedule]
        self.away_after = cfg.away_after_minutes * 60
        if self.mode == "presence" and state.get("presence_last_near") is None:
            # Nothing known yet: count from start-up, so the house arms
            # away_after minutes after the first run if no household key shows.
            state.set_state("presence_last_near", now)
        self.override: dict | None = state.get("override")
        self.armed = False
        self._auto = self._compute(now)
        self._expire_override()
        self.armed = self._effective()

    def _compute(self, now: float) -> bool:
        if self.mode == "always":
            return True
        if self.mode == "manual":
            return bool(self.state.get("armed", False))
        if self.mode == "schedule":
            return in_windows(self.windows, now, self.tz)
        last = self.state.get("presence_last_near")
        return last is None or now - last >= self.away_after

    def _expire_override(self) -> None:
        if self.override is not None and self.override.get("auto") != self._auto:
            self.override = None
            self.state.set_state("override", None)

    def _effective(self) -> bool:
        return self.override["armed"] if self.override is not None else self._auto

    def update(self, now: float) -> bool:
        self._auto = self._compute(now)
        self._expire_override()
        self.armed = self._effective()
        return self.armed

    def household_near(self, t: float) -> None:
        """A household presence key was near at time t."""
        if self.mode != "presence":
            return
        last = self.state.get("presence_last_near")
        if last is None or t > last:
            self.state.set_state("presence_last_near", t)
        self.update(t)

    def set(self, armed: bool, now: float) -> None:
        """The page's toggle (and POST /api/arm)."""
        if self.mode == "manual":
            self.state.set_state("armed", bool(armed))
        else:
            self._auto = self._compute(now)
            self.override = {"armed": bool(armed), "auto": self._auto, "at": now}
            self.state.set_state("override", self.override)
        self.update(now)

    def clear_override(self) -> None:
        self.override = None
        self.state.set_state("override", None)
        self.armed = self._auto

    def status(self) -> dict:
        return {"mode": self.mode, "armed": self.armed, "auto": self._auto,
                "override": None if self.override is None else self.override["armed"]}
