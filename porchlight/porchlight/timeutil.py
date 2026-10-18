"""Local days, hours and weekly windows. Times are UTC epoch seconds; days and
hours for the rules use the local zone (SPEC §4.10 Time)."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
LOCALTIME = "/etc/localtime"


def local_zone() -> tzinfo:
    """The Pi's time zone as a real zone, so days and hours stay right across
    DST changes: $TZ, else the zone /etc/localtime links to, else the current
    fixed offset."""
    names = [os.environ.get("TZ", "").lstrip(":")]
    target = os.path.realpath(LOCALTIME)
    if "zoneinfo/" in target:
        names.append(target.split("zoneinfo/", 1)[1])
    for name in names:
        if name:
            try:
                return ZoneInfo(name)
            except (ZoneInfoNotFoundError, ValueError):
                pass
    return datetime.now().astimezone().tzinfo


def local_dt(t: float, tz: tzinfo) -> datetime:
    return datetime.fromtimestamp(t, tz)


def local_day(t: float, tz: tzinfo) -> date:
    return local_dt(t, tz).date()


def minute_of_day(t: float, tz: tzinfo) -> int:
    d = local_dt(t, tz)
    return d.hour * 60 + d.minute


def circular_minutes(a: int, b: int) -> int:
    d = abs(a - b) % 1440
    return min(d, 1440 - d)


def fmt_local(t: float, tz: tzinfo) -> str:
    return local_dt(t, tz).strftime("%a %Y-%m-%d %H:%M")


def parse_hhmm(s: str) -> int:
    m = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*", s)
    if not m or int(m.group(1)) > 24 or int(m.group(2)) > 59 or (int(m.group(1)) == 24 and int(m.group(2))):
        raise ValueError(f"bad time {s!r}, want HH:MM")
    return int(m.group(1)) * 60 + int(m.group(2))


def parse_range(s: str) -> tuple[int, int]:
    """"HH:MM-HH:MM" in minutes of the day; may cross midnight."""
    parts = s.split("-")
    if len(parts) != 2:
        raise ValueError(f"bad range {s!r}, want HH:MM-HH:MM")
    return parse_hhmm(parts[0]), parse_hhmm(parts[1])


def in_range(minute: int, rng: tuple[int, int]) -> bool:
    start, end = rng
    if start == end:
        return True
    if start < end:
        return start <= minute < end
    return minute >= start or minute < end


def parse_days(spec: str) -> set[int]:
    """"mon-fri", "sat,sun", "fri-mon", "daily" or "*" -> weekday numbers (Mon=0)."""
    spec = spec.strip().lower()
    if spec in ("daily", "*", "all", "every day"):
        return set(range(7))
    out: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = (DAYS.index(x.strip()[:3]) if x.strip()[:3] in DAYS else _bad(spec) for x in part.split("-", 1))
            i = a
            while True:
                out.add(i)
                if i == b:
                    break
                i = (i + 1) % 7
        elif part[:3] in DAYS:
            out.add(DAYS.index(part[:3]))
        else:
            _bad(spec)
    return out


def _bad(spec: str):
    raise ValueError(f"bad days {spec!r}, want e.g. mon-fri, sat,sun or daily")


@dataclass(frozen=True)
class Window:
    """A weekly window: on `days`, from `start` to `end` (minutes). A window
    that crosses midnight belongs to the day it starts."""
    days: frozenset
    start: int
    end: int

    @classmethod
    def parse(cls, d: dict) -> "Window":
        return cls(frozenset(parse_days(d.get("days", "daily"))), parse_hhmm(d["from"]), parse_hhmm(d["to"]))

    def contains(self, t: float, tz: tzinfo) -> bool:
        dt = local_dt(t, tz)
        minute = dt.hour * 60 + dt.minute
        today, yesterday = dt.weekday(), (dt.weekday() - 1) % 7
        if self.start < self.end:
            return today in self.days and self.start <= minute < self.end
        if self.start == self.end:
            return today in self.days
        return (today in self.days and minute >= self.start) or (yesterday in self.days and minute < self.end)


def in_windows(windows, t: float, tz: tzinfo) -> bool:
    return any(w.contains(t, tz) for w in windows)


def day_start(d: date, tz: tzinfo) -> float:
    return datetime(d.year, d.month, d.day, tzinfo=tz).timestamp()


def add_days(d: date, n: int) -> date:
    return d + timedelta(days=n)
