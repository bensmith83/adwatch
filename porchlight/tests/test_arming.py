from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from porchlight.arming import Arming
from porchlight.config import Arming as ArmingConfig

TZ = ZoneInfo("UTC")
MIN = 60.0


def at(day, hour, minute=0):
    # day 0 is Monday 2026-10-19
    return (datetime(2026, 10, 19, tzinfo=TZ) + timedelta(days=day, hours=hour, minutes=minute)).timestamp()


class State(dict):
    """Stands in for the store's state table."""
    def set_state(self, k, v):
        self[k] = v


def make(mode, state=None, now=None, **kw):
    cfg = ArmingConfig(mode=mode, **kw)
    return Arming(cfg, TZ, state if state is not None else State(), now=now if now is not None else at(0, 12))


def test_always():
    a = make("always")
    assert a.update(at(0, 3)) is True
    assert a.update(at(5, 15)) is True


def test_manual_toggle_survives_restart():
    st = State()
    a = make("manual", st)
    assert a.update(at(0, 12)) is False
    a.set(True, at(0, 12))
    assert a.update(at(0, 13)) is True
    b = make("manual", st, now=at(1, 0))
    assert b.update(at(1, 0)) is True
    b.set(False, at(1, 0))
    assert b.update(at(1, 1)) is False


def test_schedule_window_crossing_midnight():
    a = make("schedule", schedule=[{"days": "mon-fri", "from": "22:00", "to": "06:00"}])
    assert a.update(at(0, 21, 59)) is False
    assert a.update(at(0, 22, 0)) is True
    assert a.update(at(1, 5, 59)) is True     # Tuesday morning, from Monday night
    assert a.update(at(1, 6, 0)) is False
    assert a.update(at(5, 23, 0)) is False    # Saturday night: no window
    assert a.update(at(5, 3, 0)) is True      # Saturday morning, from Friday night


def test_schedule_with_several_windows():
    a = make("schedule", schedule=[{"days": "mon-fri", "from": "08:30", "to": "17:30"},
                                   {"days": "sat,sun", "from": "00:00", "to": "06:00"}])
    assert a.update(at(0, 9)) is True
    assert a.update(at(5, 1)) is True
    assert a.update(at(5, 9)) is False


def test_presence_arms_after_away_after_and_disarms_at_once():
    a = make("presence", now=at(0, 12), away_after_minutes=15)
    a.household_near(at(0, 12))
    assert a.update(at(0, 12)) is False
    assert a.update(at(0, 12, 14)) is False
    assert a.update(at(0, 12) + 15 * MIN - 1) is False
    assert a.update(at(0, 12, 15)) is True
    a.household_near(at(0, 18))
    assert a.update(at(0, 18)) is False


def test_presence_starts_disarmed_and_remembers_the_last_near_time():
    st = State()
    a = make("presence", st, now=at(0, 12))
    assert a.update(at(0, 12)) is False
    a.household_near(at(0, 12, 5))
    b = make("presence", st, now=at(0, 12, 30))
    assert b.update(at(0, 12, 30)) is True, "15 min after the last near sighting, across a restart"


def test_override_lasts_until_the_next_schedule_edge():
    a = make("schedule", schedule=[{"days": "daily", "from": "08:30", "to": "17:30"}])
    assert a.update(at(0, 9)) is True
    a.set(False, at(0, 9))
    assert a.update(at(0, 9)) is False
    assert a.update(at(0, 17, 29)) is False
    assert a.override is not None
    assert a.update(at(0, 17, 30)) is False    # the edge: back to automatic (disarmed)
    assert a.override is None
    assert a.update(at(1, 8, 30)) is True


def test_override_to_armed_outside_a_window_ends_at_the_window():
    a = make("schedule", schedule=[{"days": "daily", "from": "08:30", "to": "17:30"}])
    assert a.update(at(0, 20)) is False
    a.set(True, at(0, 20))
    assert a.update(at(1, 3)) is True
    assert a.update(at(1, 8, 30)) is True      # window starts: automatic says armed anyway
    assert a.override is None
    assert a.update(at(1, 17, 30)) is False


def test_override_in_presence_mode_ends_on_a_presence_change():
    a = make("presence", now=at(0, 12), away_after_minutes=15)
    assert a.update(at(0, 12, 20)) is True     # nobody home
    a.set(False, at(0, 12, 20))
    assert a.update(at(0, 13)) is False
    a.household_near(at(0, 14))                # someone returns: a presence change
    assert a.update(at(0, 14)) is False
    assert a.override is None
    assert a.update(at(0, 14, 15)) is True     # and leaves again


def test_override_survives_a_restart():
    st = State()
    a = make("schedule", st, schedule=[{"days": "daily", "from": "08:30", "to": "17:30"}], now=at(0, 9))
    a.update(at(0, 9))
    a.set(False, at(0, 9))
    b = make("schedule", st, schedule=[{"days": "daily", "from": "08:30", "to": "17:30"}], now=at(0, 10))
    assert b.update(at(0, 10)) is False


def test_an_override_whose_edge_passed_while_down_is_dropped():
    st = State()
    a = make("schedule", st, schedule=[{"days": "daily", "from": "08:30", "to": "17:30"}], now=at(0, 9))
    a.update(at(0, 9))
    a.set(False, at(0, 9))
    b = make("schedule", st, schedule=[{"days": "daily", "from": "08:30", "to": "17:30"}], now=at(0, 20))
    assert b.update(at(0, 20)) is False
    assert b.override is None


def test_override_in_always_mode_lasts_until_cleared():
    a = make("always")
    a.set(False, at(0, 12))
    assert a.update(at(3, 12)) is False
    a.clear_override()
    assert a.update(at(3, 12)) is True


def test_status_for_the_page():
    a = make("schedule", schedule=[{"days": "daily", "from": "08:30", "to": "17:30"}])
    a.update(at(0, 9))
    s = a.status()
    assert s["mode"] == "schedule" and s["armed"] is True and s["auto"] is True and s["override"] is None


def test_a_bad_schedule_fails_at_start():
    with pytest.raises(ValueError):
        make("schedule", schedule=[{"days": "someday", "from": "08:30", "to": "17:30"}])
