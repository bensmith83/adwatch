from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from porchlight.config import Rules as RulesConfig
from porchlight.model import Unit, Visit
from porchlight.rules import AlertBook, Rules, weight

TZ = ZoneInfo("UTC")
FLOOR = -80
MIN = 60.0
DAY = 86400.0
T0 = datetime(2026, 10, 19, 12, 0, tzinfo=TZ).timestamp()


def at(day, hour, minute=0):
    return (datetime(2026, 10, 19, tzinfo=TZ) + timedelta(days=day, hours=hour, minutes=minute)).timestamp()


def unit(id=1, mobility="vehicle", label=None, baseline=False, first_seen=None, weak=False):
    return Unit(id=id, vendor="Acme", product="Car", id_types={"Serial"}, mobility=mobility, weak=weak,
                first_seen=T0 - 30 * DAY if first_seen is None else first_seen, last_seen=T0, label=label,
                baseline=baseline, hint="0001")


_ids = iter(range(1, 10_000))


def visit(start, dur=60.0, rssi=-60, uid=1):
    return Visit(id=next(_ids), unit_id=uid, start=start, end=start + dur, n=2, max_rssi=rssi, sum_rssi=2 * rssi)


@pytest.fixture
def cfg():
    return RulesConfig()


@pytest.fixture
def book():
    return AlertBook()


def run(cfg, book, u, v, history=(), armed=False, now=None):
    rules = Rules(cfg, rssi_floor=FLOOR, tz=TZ)
    return rules.evaluate(u, v, list(history), armed=armed, now=now if now is not None else v.end, alerts=book)


def rules_of(fires):
    return [f.rule for f in fires]


# --- weights ---------------------------------------------------------------------

@pytest.mark.parametrize("mobility, w", [
    ("vehicle", "high"), ("personal", "high"), ("in_transit", "high"),
    ("unknown", "medium"), ("fixed", "low"), ("movable", "low"),
])
def test_weights(mobility, w):
    assert weight(mobility) == w


# --- R1 ----------------------------------------------------------------------------

def test_r1_fires_exactly_at_linger_minutes(cfg, book):
    u = unit()
    assert run(cfg, book, u, visit(T0, dur=10 * MIN - 1)) == []
    (f,) = run(cfg, book, u, visit(T0, dur=10 * MIN))
    assert f.rule == "R1" and f.severity == "alert"


def test_r1_needs_a_near_visit(cfg, book):
    assert run(cfg, book, unit(), visit(T0, dur=20 * MIN, rssi=FLOOR - 1)) == []
    assert rules_of(run(cfg, book, unit(), visit(T0, dur=20 * MIN, rssi=FLOOR))) == ["R1"]


def test_r1_once_per_visit(cfg, book):
    u, v = unit(), visit(T0, dur=10 * MIN)
    for f in run(cfg, book, u, v):
        book.add(u.id, f, created=v.end)
    v.end += 30 * MIN
    assert run(cfg, book, u, v, now=v.end) == []


def test_r1_severity_by_weight(cfg, book):
    assert run(cfg, book, unit(mobility="unknown"), visit(T0, dur=10 * MIN))[0].severity == "alert"
    (f,) = run(cfg, book, unit(mobility="fixed"), visit(T0, dur=10 * MIN))
    assert f.severity == "info"
    assert "new fixed device nearby" in f.details["title"].lower()


def test_r1_skips_known_units(cfg, book):
    for u in (unit(label="known"), unit(label="household"), unit(label="ignore"), unit(baseline=True)):
        assert "R1" not in rules_of(run(cfg, book, u, visit(T0, dur=20 * MIN)))


def test_r1_weak_units_say_so(cfg, book):
    (f,) = run(cfg, book, unit(weak=True), visit(T0, dur=10 * MIN))
    assert f.details["weak"] is True
    assert "weak ID, may be a different device" in f.details["message"]


# --- R2 ----------------------------------------------------------------------------

def three_evenings(days=(0, 1, 2), hour=19):
    return [visit(at(d, hour)) for d in days]


def test_r2_fires_on_the_third_distinct_day(cfg, book):
    h = three_evenings()
    u = unit(mobility="personal")
    assert "R2" not in rules_of(run(cfg, book, u, h[1], history=h[:1]))
    (f,) = [f for f in run(cfg, book, u, h[2], history=h[:2]) if f.rule == "R2"]
    assert f.severity == "alert"
    assert len(f.details["visits"]) == 3


def test_r2_counts_days_not_visits(cfg, book):
    h = [visit(at(0, 8)), visit(at(0, 12)), visit(at(0, 19))]
    assert "R2" not in rules_of(run(cfg, book, unit(), visit(at(1, 9)), history=h))


def test_r2_only_counts_days_inside_the_window(cfg, book):
    old = visit(at(-14, 11))           # just outside 14 days of the visit below
    h = [old, visit(at(-5, 19))]
    assert "R2" not in rules_of(run(cfg, book, unit(), visit(at(0, 12)), history=h))
    inside = visit(at(-14, 13))        # just inside
    assert "R2" in rules_of(run(cfg, book, unit(), visit(at(0, 12)), history=[inside, h[1]]))


def test_r2_ignores_far_visits(cfg, book):
    h = [visit(at(0, 19), rssi=FLOOR - 5), visit(at(1, 19))]
    assert "R2" not in rules_of(run(cfg, book, unit(), visit(at(2, 19)), history=h))


def test_r2_skips_fixed_and_movable_units(cfg, book):
    h = three_evenings()
    for m in ("fixed", "movable"):
        assert "R2" not in rules_of(run(cfg, book, unit(mobility=m), h[2], history=h[:2]))


def test_r2_fires_once_then_again_only_after_ack_and_more_days(cfg, book):
    u = unit(mobility="personal")
    h = three_evenings()
    (f,) = [f for f in run(cfg, book, u, h[2], history=h[:2]) if f.rule == "R2"]
    a = book.add(u.id, f, created=h[2].end)
    later = [visit(at(d, 19)) for d in (3, 4, 5)]
    # not acknowledged: never again
    assert "R2" not in rules_of(run(cfg, book, u, later[2], history=h + later[:2], now=later[2].end + 40 * MIN))
    book.ack(a.id)
    # acknowledged: needs repeat_days more distinct days after it
    assert "R2" not in rules_of(run(cfg, book, u, later[1], history=h + later[:1], now=later[1].end + 40 * MIN))
    assert "R2" in rules_of(run(cfg, book, u, later[2], history=h + later[:2], now=later[2].end + 40 * MIN))


# --- R3 ----------------------------------------------------------------------------

def new_unit_in(v, **kw):
    return unit(first_seen=v.start, **kw)


def test_r3_fires_at_the_armed_dwell(cfg, book):
    v = visit(T0, dur=59)
    assert run(cfg, book, new_unit_in(v), v, armed=True) == []
    v = visit(T0, dur=60)
    (f,) = run(cfg, book, new_unit_in(v), v, armed=True)
    assert f.rule == "R3" and f.severity == "alert"


def test_r3_zero_dwell_fires_at_once(cfg, book):
    cfg.armed_min_dwell_seconds = 0
    v = visit(T0, dur=0)
    assert rules_of(run(cfg, book, new_unit_in(v), v, armed=True)) == ["R3"]


def test_r3_needs_armed_near_and_new(cfg, book):
    v = visit(T0, dur=120)
    assert run(cfg, book, new_unit_in(v), v, armed=False) == []
    far = visit(T0, dur=120, rssi=FLOOR - 1)
    assert run(cfg, book, new_unit_in(far), far, armed=True) == []
    assert run(cfg, book, unit(first_seen=v.start - 1), v, armed=True) == []


def test_r3_any_mobility_once_per_unit(cfg, book):
    v = visit(T0, dur=120)
    u = new_unit_in(v, mobility="fixed")
    (f,) = run(cfg, book, u, v, armed=True)
    book.add(u.id, f, created=v.end)
    v2 = visit(T0 + DAY, dur=120)
    u.first_seen = v2.start  # even if it somehow looked new again
    assert run(cfg, book, u, v2, armed=True, now=v2.end) == []


# --- R4 ----------------------------------------------------------------------------

def usual_evenings():
    # 6 visits on 3 days, starting 17:00-18:30
    return [visit(at(d, h, m)) for d in (-6, -4, -2) for h, m in ((17, 0), (18, 30))]


def test_r4_fires_for_a_known_unit_at_an_odd_hour(cfg, book):
    (f,) = run(cfg, book, unit(label="known"), visit(at(0, 3)), history=usual_evenings())
    assert f.rule == "R4" and f.severity == "warn"


def test_r4_within_an_hour_of_a_usual_start_is_fine(cfg, book):
    h = usual_evenings()
    assert run(cfg, book, unit(label="known"), visit(at(0, 16, 0)), history=h) == []    # 60 min before 17:00
    assert run(cfg, book, unit(label="known"), visit(at(0, 19, 30)), history=h) == []   # 60 min after 18:30
    assert rules_of(run(cfg, book, unit(label="known"), visit(at(0, 15, 59)), history=h)) == ["R4"]


def test_r4_hour_distance_wraps_midnight(cfg, book):
    h = [visit(at(d, 23, 30)) for d in (-6, -4, -2)] + [visit(at(d, 23, 45)) for d in (-6, -4)]
    assert run(cfg, book, unit(label="known"), visit(at(0, 0, 15)), history=h) == []


def test_r4_needs_five_visits_on_three_days(cfg, book):
    h = usual_evenings()
    assert run(cfg, book, unit(label="known"), visit(at(0, 3)), history=h[:4]) == []      # 4 visits
    same_days = [visit(at(d, 17, m)) for d in (-6, -4) for m in (0, 10, 20)]             # 6 visits, 2 days
    assert run(cfg, book, unit(label="known"), visit(at(0, 3)), history=same_days) == []


def test_r4_applies_to_baselined_mobile_units_only(cfg, book):
    h = usual_evenings()
    assert rules_of(run(cfg, book, unit(baseline=True, mobility="vehicle"), visit(at(0, 3)), history=h)) == ["R4"]
    assert run(cfg, book, unit(baseline=True, mobility="fixed"), visit(at(0, 3)), history=h) == []
    assert run(cfg, book, unit(label="household"), visit(at(0, 3)), history=h) == []
    assert run(cfg, book, unit(label="ignore"), visit(at(0, 3)), history=h) == []


def test_r4_quiet_hours(cfg, book):
    cfg.quiet_hours = "00:00-05:00"
    h = [visit(at(d, 1, 0)) for d in (-6, -4, -2)] + [visit(at(d, 1, 30)) for d in (-6, -4)]
    (f,) = run(cfg, book, unit(label="known"), visit(at(0, 1, 10)), history=h)
    assert f.rule == "R4" and f.details.get("quiet_hours")


def test_r4_once_per_visit_and_near_only(cfg, book):
    h = usual_evenings()
    v = visit(at(0, 3))
    u = unit(label="known")
    (f,) = run(cfg, book, u, v, history=h)
    book.add(u.id, f, created=v.end)
    assert run(cfg, book, u, v, history=h, now=v.end + 40 * MIN) == []
    assert run(cfg, book, u, visit(at(1, 3), rssi=FLOOR - 1), history=h) == []


# --- cooldown -----------------------------------------------------------------------

def test_cooldown_spans_rules(cfg, book):
    u = unit(mobility="personal")
    h = three_evenings()
    v = h[2]
    v.end = v.start + 10 * MIN
    fires = run(cfg, book, u, v, history=h[:2])
    assert rules_of(fires) == ["R1"], "one alert per cooldown, even when two rules match"
    book.add(u.id, fires[0], created=v.end)
    assert run(cfg, book, u, v, history=h[:2], now=v.end + 30 * MIN - 1) == []
    assert rules_of(run(cfg, book, u, v, history=h[:2], now=v.end + 30 * MIN)) == ["R2"]


def test_info_entries_do_not_start_a_cooldown(cfg, book):
    u = unit(mobility="fixed", id=7)
    v = visit(T0, dur=10 * MIN)
    (f,) = run(cfg, book, u, v)
    book.add(u.id, f, created=v.end)
    assert book.in_cooldown(u.id, v.end + 1, cfg.cooldown_minutes * MIN) is False
