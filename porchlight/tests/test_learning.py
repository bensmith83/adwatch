from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from porchlight.learning import Learning
from porchlight.model import Unit, Visit

TZ = ZoneInfo("UTC")
DAY = 86400.0
FLOOR = -80


def at(day, hour=12):
    return (datetime(2026, 10, 19, tzinfo=TZ) + timedelta(days=day, hours=hour)).timestamp()


class State(dict):
    def set_state(self, k, v):
        self[k] = v


def unit(id, mobility, label=None):
    return Unit(id=id, mobility=mobility, label=label, first_seen=at(0), last_seen=at(0))


def v(id, uid, day, rssi=-60):
    return Visit(id=id, unit_id=uid, start=at(day), end=at(day) + 60, n=1, max_rssi=rssi, sum_rssi=rssi)


def test_learning_lasts_learning_days_from_first_run():
    st = State()
    l = Learning(7, st, now=at(0))
    assert st["learning_started"] == at(0)
    assert l.active(at(0)) and l.active(at(7) - 1)
    assert not l.due(at(7) - 1)
    assert l.due(at(7))


def test_learning_start_survives_restart():
    st = State()
    Learning(7, st, now=at(0))
    l2 = Learning(7, st, now=at(3))
    assert l2.started == at(0)


def test_baseline_picks_neighbours_fixed_things_and_regulars():
    units = {
        1: unit(1, "fixed"),        # near once: a neighbour's thing
        2: unit(2, "movable"),      # only ever far: stays unknown
        3: unit(3, "personal"),     # 3 days: a regular
        4: unit(4, "vehicle"),      # 2 days: stays unknown
        5: unit(5, "fixed", label="ignore"),
    }
    history = {
        1: [v(1, 1, 0)],
        2: [v(2, 2, 0, rssi=-90), v(3, 2, 1, rssi=-90)],
        3: [v(4, 3, 0, rssi=-90), v(5, 3, 2, rssi=-90), v(6, 3, 4, rssi=-90)],
        4: [v(7, 4, 0), v(8, 4, 1), v(9, 4, 1)],
    }
    st = State()
    l = Learning(7, st, now=at(0))
    got = l.finish(units, history, open_visits={}, rssi_floor=FLOOR, tz=TZ)
    assert got == {1, 3}
    assert units[1].baseline and units[3].baseline
    assert not units[2].baseline and not units[4].baseline
    assert units[5].label == "ignore"
    assert not l.active(at(8)) and not l.due(at(8))
    assert st["learning_done"] is True


def test_open_visits_count_too():
    units = {1: unit(1, "fixed")}
    l = Learning(7, State(), now=at(0))
    assert l.finish(units, {}, open_visits={1: v(1, 1, 6)}, rssi_floor=FLOOR, tz=TZ) == {1}


def test_relearn_resets_baseline_and_keeps_labels():
    units = {1: unit(1, "fixed"), 2: unit(2, "vehicle", label="known")}
    units[1].baseline = units[2].baseline = True
    st = State()
    l = Learning(7, st, now=at(0))
    l.finish(units, {}, {}, FLOOR, TZ)
    l.relearn(units, now=at(10))
    assert not units[1].baseline and not units[2].baseline
    assert units[2].label == "known"
    assert l.active(at(10)) and st["learning_started"] == at(10) and st["learning_done"] is False


def test_status():
    l = Learning(7, State(), now=at(0))
    s = l.status(at(1))
    assert s["active"] is True and s["ends"] == at(7)
