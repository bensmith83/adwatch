import pytest

from porchlight.model import Visit
from porchlight.store import Store
from porchlight.visits import CHECKPOINT_S, VisitTracker

GAP = 300.0


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "p.db")
    yield s
    s.close()


@pytest.fixture
def vt(store):
    return VisitTracker(gap_s=GAP, rssi_floor=-80, store=store)


def test_first_sighting_opens_a_visit(vt):
    v, closed = vt.sight(1, 100.0, -70)
    assert closed is None
    assert (v.unit_id, v.start, v.end, v.n, v.max_rssi, v.avg_rssi) == (1, 100.0, 100.0, 1, -70, -70.0)
    assert vt.open[1] is v


def test_sightings_within_the_gap_extend_the_visit(vt):
    v, _ = vt.sight(1, 0.0, -70)
    v2, closed = vt.sight(1, GAP, -60)          # exactly the gap: same visit
    assert v2 is v and closed is None
    assert (v.end, v.n, v.max_rssi, v.avg_rssi) == (GAP, 2, -60, -65.0)


def test_a_longer_gap_starts_a_new_visit_and_closes_the_old(vt, store):
    v, _ = vt.sight(1, 0.0, -70)
    v2, closed = vt.sight(1, GAP + 0.001, -70)
    assert closed is v and v2 is not v
    assert v2.start == GAP + 0.001 and v2.id != v.id
    assert vt.history[1] == [v]
    store.flush()
    assert [x.id for x in store.load().visits] == [v.id], "the open visit waits for a checkpoint"


def test_sweep_closes_visits_once_the_gap_has_passed(vt):
    v, _ = vt.sight(1, 0.0, -70)
    assert vt.sweep(GAP) == []
    assert vt.sweep(GAP + 1) == [v]
    assert 1 not in vt.open
    assert vt.history[1] == [v]


def test_near_is_max_rssi_at_or_above_the_floor(vt):
    v, _ = vt.sight(1, 0.0, -81)
    assert not vt.is_near(v)
    vt.sight(1, 1.0, -80)
    assert vt.is_near(v)


def test_closed_visits_are_written(vt, store):
    v, _ = vt.sight(1, 0.0, -70)
    vt.sweep(GAP + 1)
    store.flush()
    (saved,) = store.load().visits
    assert saved.id == v.id and saved.n == 1


def test_open_visits_are_checkpointed_every_60s(vt, store):
    v, _ = vt.sight(1, 0.0, -70)
    assert vt.checkpoint(0.0)
    store.flush()
    assert [x.id for x in store.load().visits] == [v.id]
    vt.sight(1, 10.0, -60)
    assert not vt.checkpoint(CHECKPOINT_S - 1)
    store.flush()
    assert store.load().visits[0].n == 1
    assert vt.checkpoint(CHECKPOINT_S)
    store.flush()
    assert store.load().visits[0].n == 2
    assert CHECKPOINT_S == 60


def test_merge_combines_open_visits_and_moves_history(vt, store):
    old_b, _ = vt.sight(2, 0.0, -75)
    vt.sweep(GAP + 1)
    a, _ = vt.sight(1, 1000.0, -70)
    b, _ = vt.sight(2, 900.0, -60)
    vt.checkpoint(1000.0)
    store.flush()
    vt.merge(keep=1, gone=2)
    assert 2 not in vt.open
    m = vt.open[1]
    assert (m.start, m.end, m.n, m.max_rssi) == (900.0, 1000.0, 2, -60)
    assert m.unit_id == 1
    assert [h.id for h in vt.history[1]] == [old_b.id]
    assert old_b.unit_id == 1
    store.flush()
    assert b.id not in [x.id for x in store.load().visits]


def test_restore_reopens_recent_visits(store):
    store.put_visit(Visit(id=1, unit_id=1, start=0.0, end=1000.0, n=3, max_rssi=-70, sum_rssi=-210.0))
    store.put_visit(Visit(id=2, unit_id=2, start=0.0, end=100.0, n=1, max_rssi=-70, sum_rssi=-70.0))
    store.flush()
    vt = VisitTracker(gap_s=GAP, rssi_floor=-80, store=store)
    vt.restore(store.load(), now=1100.0)
    assert set(vt.open) == {1}
    assert [v.id for v in vt.history[2]] == [2]
    v, _ = vt.sight(3, 1100.0, -70)
    assert v.id == 3, "ids continue after the stored ones"


def test_remove_forgets_units(vt):
    vt.sight(1, 0.0, -70)
    vt.remove({1})
    assert 1 not in vt.open and 1 not in vt.history


def test_prune_history(vt):
    vt.sight(1, 0.0, -70)
    vt.sweep(GAP + 1)
    vt.sight(1, 10_000.0, -70)
    vt.sweep(10_000.0 + GAP + 1)
    vt.prune(before=5000.0)
    assert [v.start for v in vt.history[1]] == [10_000.0]
