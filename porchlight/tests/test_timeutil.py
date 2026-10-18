from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from porchlight.timeutil import Window, in_windows, local_day, minute_of_day, parse_days, parse_range

TZ = ZoneInfo("Asia/Tokyo")   # UTC+9, no DST


def ts(y, mo, d, h=0, mi=0, tz=TZ):
    return datetime(y, mo, d, h, mi, tzinfo=tz).timestamp()


def test_local_day_uses_the_local_zone():
    t = datetime(2026, 10, 16, 20, 0, tzinfo=ZoneInfo("UTC")).timestamp()  # 05:00 on the 17th in Tokyo
    assert local_day(t, TZ).isoformat() == "2026-10-17"
    assert minute_of_day(t, TZ) == 5 * 60


@pytest.mark.parametrize("spec, days", [
    ("mon-fri", {0, 1, 2, 3, 4}),
    ("sat,sun", {5, 6}),
    ("fri-mon", {4, 5, 6, 0}),
    ("daily", set(range(7))),
    ("*", set(range(7))),
    ("Tue", {1}),
    ("mon-wed,fri", {0, 1, 2, 4}),
])
def test_parse_days(spec, days):
    assert parse_days(spec) == days


def test_bad_days_are_rejected():
    with pytest.raises(ValueError):
        parse_days("someday")


def test_parse_range():
    assert parse_range("00:00-05:00") == (0, 300)
    assert parse_range("22:30-06:15") == (1350, 375)
    with pytest.raises(ValueError):
        parse_range("25:00-01:00")


def test_a_same_day_window():
    w = Window.parse({"days": "mon-fri", "from": "08:30", "to": "17:30"})
    # 2026-10-19 is a Monday
    assert not in_windows([w], ts(2026, 10, 19, 8, 29), TZ)
    assert in_windows([w], ts(2026, 10, 19, 8, 30), TZ)
    assert in_windows([w], ts(2026, 10, 19, 17, 29), TZ)
    assert not in_windows([w], ts(2026, 10, 19, 17, 30), TZ)
    assert not in_windows([w], ts(2026, 10, 18, 12, 0), TZ)   # Sunday


def test_a_window_crossing_midnight_belongs_to_the_day_it_starts():
    w = Window.parse({"days": "fri", "from": "22:00", "to": "06:00"})
    # 2026-10-23 is a Friday
    assert not in_windows([w], ts(2026, 10, 23, 21, 59), TZ)
    assert in_windows([w], ts(2026, 10, 23, 22, 0), TZ)
    assert in_windows([w], ts(2026, 10, 24, 5, 59), TZ)       # Saturday morning
    assert not in_windows([w], ts(2026, 10, 24, 6, 0), TZ)
    assert not in_windows([w], ts(2026, 10, 24, 23, 0), TZ)   # Saturday night is not Friday's
    assert not in_windows([w], ts(2026, 10, 23, 3, 0), TZ)    # Friday morning is Thursday's


def test_next_edge():
    w = Window.parse({"days": "daily", "from": "08:00", "to": "09:00"})
    assert in_windows([w], ts(2026, 10, 19, 8, 0), TZ)


def test_local_zone_is_a_real_zone_that_knows_dst(monkeypatch):
    from porchlight.timeutil import local_zone
    monkeypatch.setenv("TZ", "America/New_York")
    tz = local_zone()
    summer = datetime(2026, 7, 1, 12, tzinfo=tz).utcoffset().total_seconds()
    winter = datetime(2026, 12, 1, 12, tzinfo=tz).utcoffset().total_seconds()
    assert (summer, winter) == (-4 * 3600, -5 * 3600)


def test_local_zone_reads_etc_localtime(monkeypatch, tmp_path):
    from porchlight import timeutil
    monkeypatch.delenv("TZ", raising=False)
    link = tmp_path / "localtime"
    link.symlink_to("/usr/share/zoneinfo/Europe/Berlin")
    monkeypatch.setattr(timeutil, "LOCALTIME", str(link))
    assert str(timeutil.local_zone()) == "Europe/Berlin"
