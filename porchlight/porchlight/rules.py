"""The four alarm rules and the alert book (SPEC §4.6).

R1 lingering stranger, R2 repeat visitor, R3 new while armed, R4 known at
odd hours. Rules are evaluated on each sighting of a unit, against its
current visit and its closed visits. A per-unit cooldown spans all rules;
`info` entries are never pushed and neither start nor wait for it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import tzinfo

from .config import Rules as RulesConfig
from .model import SEVERITY_RANK, Alert, Unit, Visit
from .timeutil import circular_minutes, fmt_local, in_range, local_day, minute_of_day, parse_range

HIGH_MOBILITY = ("vehicle", "personal", "in_transit")
LOW_MOBILITY = ("fixed", "movable")
DAY_S = 86400.0
WEAK_NOTE = "weak ID, may be a different device"


def weight(mobility: str) -> str:
    if mobility in HIGH_MOBILITY:
        return "high"
    if mobility in LOW_MOBILITY:
        return "low"
    return "medium"


def describe(u: Unit) -> str:
    """A unit as shown everywhere: name or product, vendor, ID types and a
    4-character hint. Never the identifier itself."""
    what = u.label_name or u.product or "Unknown device"
    parts = [p for p in (u.vendor if u.vendor and u.vendor not in what else None,
                         ", ".join(sorted(u.id_types)) or None) if p]
    hint = f"…{u.hint}" if u.hint else ""
    return f"{what} ({'; '.join(parts + ([hint] if hint else []))})" if parts or hint else what


@dataclass
class Fire:
    rule: str
    severity: str
    details: dict = field(default_factory=dict)


class AlertBook:
    def __init__(self, alerts: list[Alert] | None = None, next_id: int = 1):
        self.alerts: dict[int, Alert] = {a.id: a for a in alerts or []}
        self._next_id = max([next_id] + [a.id + 1 for a in self.alerts.values()])

    def add(self, unit_id: int, fire: Fire, created: float) -> Alert:
        a = Alert(id=self._next_id, unit_id=unit_id, rule=fire.rule, severity=fire.severity, created=created,
                  details=dict(fire.details))
        self._next_id += 1
        self.alerts[a.id] = a
        return a

    def ack(self, alert_id: int) -> Alert | None:
        a = self.alerts.get(alert_id)
        if a:
            a.acked = True
        return a

    def for_unit(self, unit_id: int, rule: str | None = None) -> list[Alert]:
        return [a for a in self.alerts.values() if a.unit_id == unit_id and (rule is None or a.rule == rule)]

    def fired(self, unit_id: int, rule: str, visit_id: int | None = None) -> bool:
        return any(visit_id is None or a.details.get("visit") == visit_id for a in self.for_unit(unit_id, rule))

    def last(self, unit_id: int, rule: str) -> Alert | None:
        found = self.for_unit(unit_id, rule)
        return max(found, key=lambda a: a.created) if found else None

    def in_cooldown(self, unit_id: int, now: float, cooldown_s: float) -> bool:
        return any(a.severity != "info" and 0 <= now - a.created < cooldown_s for a in self.for_unit(unit_id))

    def reassign(self, keep: int, gone: int) -> list[Alert]:
        moved = [a for a in self.alerts.values() if a.unit_id == gone]
        for a in moved:
            a.unit_id = keep
        return moved

    def remove_units(self, unit_ids) -> None:
        self.alerts = {i: a for i, a in self.alerts.items() if a.unit_id not in unit_ids}

    def prune(self, before: float) -> None:
        self.alerts = {i: a for i, a in self.alerts.items() if a.created >= before}


class Rules:
    def __init__(self, cfg: RulesConfig, rssi_floor: int, tz: tzinfo):
        self.cfg = cfg
        self.floor = rssi_floor
        self.tz = tz
        self.quiet = parse_range(cfg.quiet_hours) if cfg.quiet_hours else None

    def evaluate(self, u: Unit, v: Visit, history: list[Visit], armed: bool, now: float,
                 alerts: AlertBook) -> list[Fire]:
        if u.label in ("household", "ignore"):
            return []
        near = v.max_rssi >= self.floor
        if not near:
            return []
        candidates: list[Fire] = []
        if not u.known:
            candidates += filter(None, (
                self._r3(u, v, armed, alerts),
                self._r1(u, v, alerts),
                self._r2(u, v, history, now, alerts),
            ))
        r4 = self._r4(u, v, history, alerts)
        if r4:
            candidates.append(r4)

        out: list[Fire] = []
        cooling = alerts.in_cooldown(u.id, now, self.cfg.cooldown_minutes * 60)
        for f in candidates:
            if f.severity == "info":
                out.append(f)
            elif not cooling:
                out.append(f)
                cooling = True   # one pushed alert per cooldown
        for f in out:
            f.details.setdefault("visit", v.id)
            f.details.setdefault("weak", u.weak)
            if u.weak:
                f.details["message"] += f" ({WEAK_NOTE})"
        return out

    # --- the rules ------------------------------------------------------------

    def _r1(self, u: Unit, v: Visit, alerts: AlertBook) -> Fire | None:
        if v.duration < self.cfg.linger_minutes * 60 or alerts.fired(u.id, "R1", v.id):
            return None
        mins = round(v.duration / 60)
        if weight(u.mobility) == "low":
            return Fire("R1", "info", {"title": "New fixed device nearby",
                                       "message": f"{describe(u)} near for {mins} min, max {v.max_rssi} dBm"})
        return Fire("R1", "alert", {"title": "Lingering stranger",
                                    "message": f"{describe(u)} has been near for {mins} min, max {v.max_rssi} dBm",
                                    "dwell_s": round(v.duration), "max_rssi": v.max_rssi})

    def _r2(self, u: Unit, v: Visit, history: list[Visit], now: float, alerts: AlertBook) -> Fire | None:
        if u.mobility in LOW_MOBILITY:
            return None
        last = alerts.last(u.id, "R2")
        if last is not None and not last.acked:
            return None
        since = now - self.cfg.repeat_window_days * DAY_S
        visits = [x for x in history + [v] if x.max_rssi >= self.floor and x.start >= since]
        if last is not None:
            after = local_day(last.created, self.tz)
            visits = [x for x in visits if local_day(x.start, self.tz) > after]
        days = {local_day(x.start, self.tz) for x in visits}
        if len(days) < self.cfg.repeat_days:
            return None
        times = [fmt_local(x.start, self.tz) for x in sorted(visits, key=lambda x: x.start)]
        return Fire("R2", "alert", {"title": "Repeat visitor",
                                    "message": f"{describe(u)} came back on {len(days)} days: {', '.join(times)}",
                                    "visits": times, "days": len(days)})

    def _r3(self, u: Unit, v: Visit, armed: bool, alerts: AlertBook) -> Fire | None:
        if not armed or u.first_seen < v.start or v.duration < self.cfg.armed_min_dwell_seconds:
            return None
        if alerts.fired(u.id, "R3"):
            return None
        return Fire("R3", "alert", {"title": "New device while armed",
                                    "message": f"{describe(u)} appeared while armed, max {v.max_rssi} dBm",
                                    "max_rssi": v.max_rssi})

    def _r4(self, u: Unit, v: Visit, history: list[Visit], alerts: AlertBook) -> Fire | None:
        eligible = u.label == "known" or (u.label is None and u.baseline and u.mobility not in LOW_MOBILITY)
        if not eligible or alerts.fired(u.id, "R4", v.id):
            return None
        start = minute_of_day(v.start, self.tz)
        when = fmt_local(v.start, self.tz)
        if self.quiet and in_range(start, self.quiet):
            return Fire("R4", "warn", {"title": "Known device during quiet hours",
                                       "message": f"{describe(u)} arrived {when}, inside quiet hours",
                                       "quiet_hours": True})
        past = [x for x in history if x.max_rssi >= self.floor and x.id != v.id]
        if len(past) < 5 or len({local_day(x.start, self.tz) for x in past}) < 3:
            return None
        if any(circular_minutes(minute_of_day(x.start, self.tz), start) <= 60 for x in past):
            return None
        return Fire("R4", "warn", {"title": "Known device at an odd hour",
                                   "message": f"{describe(u)} arrived {when}, outside its usual hours"})


def pushable(a: Alert, min_severity: str) -> bool:
    return a.severity != "info" and SEVERITY_RANK[a.severity] >= SEVERITY_RANK[min_severity]
