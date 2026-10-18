"""SPEC §6 replay scenarios: synthetic captures through the real parser."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

import captures as C
from porchlight.config import Config
from porchlight.engine import Engine
from porchlight.resolver import FieldTable
from porchlight.replay import replay
from porchlight.sidecar import Sidecar
from porchlight.store import Store
from parser_paths import BIN, FIELDS, needs_bin

TABLE = FieldTable.load(FIELDS)
TZ = ZoneInfo("UTC")
MIN, DAY = 60.0, 86400.0
D0 = datetime(2026, 10, 19, tzinfo=TZ)   # a Monday

pytestmark = needs_bin


def at(day, hour, minute=0):
    return (D0 + timedelta(days=day, hours=hour, minutes=minute)).timestamp()


class Run:
    def __init__(self, tmp_path, learning_days=0, mode="manual"):
        cfg = Config()
        cfg.learning.learning_days = learning_days
        cfg.arming.mode = mode
        self.tmp_path = tmp_path
        self.engine = Engine(cfg, TABLE, Store(tmp_path / "p.db"), now=at(0, 0), tz=TZ)
        self.arming = []
        self.engine.on_arming.append(lambda armed: self.arming.append((self.engine.now, armed)))
        self.n = 0

    async def play(self, *streams):
        self.n += 1
        cap = C.write(self.tmp_path / f"cap{self.n}.jsonl", *streams)
        sc = Sidecar([str(BIN)])
        await sc.start()
        try:
            return await replay(cap, self.engine, sc.parse)
        finally:
            await sc.stop()

    def entries(self, severity=None):
        return [a for a in self.engine.alerts.alerts.values() if severity is None or a.severity in severity]

    def rules(self, severity=("alert", "warn")):
        return [a.rule for a in self.entries(severity)]


@pytest.fixture
def run(tmp_path):
    r = Run(tmp_path)
    yield r
    r.engine.store.close()


async def test_neighbours_fixed_devices_all_week_raise_no_alerts(tmp_path):
    r = Run(tmp_path, learning_days=7)
    speakers = [C.stay(C.sonos(f"c0ffee0000{i:02x}", f"{0xA0 + i:04X}"), at(0, 0), 8 * DAY, 120,
                       rssi=-74 - i, addr=C.fixed(f"C0:FF:EE:00:01:{i:02X}")) for i in range(3)]
    stats = await r.play(*speakers)
    assert stats.ads > 10_000 and stats.dropped == 0
    assert len(r.engine.units.units) == 3, "each speaker is one unit"
    assert all(u.mobility == "fixed" for u in r.engine.units.units.values())
    assert r.rules() == [], "no alerts, not even would-have ones"
    assert all(u.baseline for u in r.engine.units.units.values()), "baselined when learning ended"
    r.engine.store.close()


async def test_a_drive_by_is_nothing(run):
    await run.play(C.stay(C.tesla("0123456789abcdef"), at(0, 12), 20, 1, rssi=-70, addr=C.rotating("5C:FF:EE:00")))
    assert run.entries() == []
    (u,) = run.engine.units.units.values()
    assert u.mobility == "vehicle"


async def test_a_car_parked_near_for_20_minutes_is_r1(run):
    await run.play(C.stay(C.tesla("0123456789abcdef"), at(0, 12), 20 * MIN, 5, rssi=-65,
                          addr=C.rotating("5C:FF:EE:00", every_s=300)))
    assert len(run.engine.units.units) == 1, "the name survives address rotation"
    assert run.rules() == ["R1"]
    (a,) = run.entries()
    assert a.created == pytest.approx(at(0, 12, 10), abs=10)


async def test_the_same_watch_on_three_evenings_is_r2(run):
    evenings = [C.stay(C.whoop("4TEST0001"), at(d, 19), 5 * MIN, 10, rssi=-70,
                       addr=C.rotating(f"5C:FF:E{d}:00")) for d in range(3)]
    await run.play(*evenings)
    assert run.rules() == ["R2"]
    (a,) = run.entries()
    assert len(a.details["visits"]) == 3
    assert a.created >= at(2, 19)


async def test_armed_and_new_earbuds_near_for_2_minutes_is_r3(tmp_path):
    r = Run(tmp_path, mode="always")
    await r.play(C.stay(C.shokz("c0ffee0000a1"), at(0, 14), 2 * MIN, 2, rssi=-60, addr=C.rotating("5C:FF:EE:01")))
    assert r.rules() == ["R3"]
    (a,) = r.entries()
    assert a.created == pytest.approx(at(0, 14, 1), abs=3)
    r.engine.store.close()


async def test_a_known_car_at_3am_when_it_only_came_17_to_19_is_r4(run):
    car = C.tesla("fedcba9876543210")
    history = [C.stay(car, at(d, h, 30), 20 * MIN, 30, rssi=-66, addr=C.rotating(f"5C:FF:E{d}:0{h - 17}"))
               for d in range(5) for h in (17, 18)]
    await run.play(*history)
    (u,) = run.engine.units.units.values()
    run.engine.label(u.id, "known", "Next door's car")
    await run.play(C.stay(car, at(6, 3), 10 * MIN, 30, rssi=-66, addr=C.rotating("5C:FF:EE:09")))
    late = [a for a in run.entries(("alert", "warn")) if a.created >= at(6, 0)]
    assert [(a.rule, a.severity) for a in late] == [("R4", "warn")]


async def test_presence_mode_arms_15_minutes_after_the_household_watch_leaves(tmp_path):
    r = Run(tmp_path, mode="presence")
    watch = C.whoop("4TEST0002")
    await r.play(C.stay(watch, at(0, 7), 30 * MIN, 10, rssi=-60, addr=C.rotating("5C:FF:EE:02")))
    (u,) = r.engine.units.units.values()
    r.engine.label(u.id, "household", "My watch")
    left = at(0, 8)
    await r.play(C.stay(watch, at(0, 7, 31), left - at(0, 7, 31), 10, rssi=-60, addr=C.rotating("5C:FF:EE:03")),
                 [C.sonos("c0ffee0000ff", "00FF")(int(at(0, 9) * 1000), "C0:FF:EE:00:02:01", -85)])
    armed_at = [t for t, armed in r.arming if armed]
    assert armed_at, "armed once the watch left"
    assert left + 15 * MIN <= armed_at[-1] <= left + 15 * MIN + 10
    r.engine.store.close()
