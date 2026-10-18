import os
import sqlite3
import stat

import pytest

from porchlight.model import Alert, KeyInfo, Unit, Visit
from porchlight.store import FLUSH_INTERVAL_S, Store

DAY = 86400.0


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "p.db")
    yield s
    s.close()


def unit(id=1, **kw):
    d = dict(id=id, vendor="Sonos", product="Era 100", id_types={"Vendor device ID"}, mobility="fixed",
             weak=False, first_seen=1000.0, last_seen=2000.0, hint="3F2A")
    d.update(kw)
    return Unit(**d)


def test_secret_is_created_0600_and_reused(tmp_path):
    s1 = Store(tmp_path / "p.db")
    secret = tmp_path / "secret"
    assert secret.exists()
    assert stat.S_IMODE(os.stat(secret).st_mode) == 0o600
    h = s1.hmac("id:whoop:serial:TEST0001")
    s1.close()
    s2 = Store(tmp_path / "p.db")
    assert s2.hmac("id:whoop:serial:TEST0001") == h
    s2.close()


def test_a_different_secret_gives_different_hmacs(tmp_path):
    a = Store(tmp_path / "a" / "p.db")
    b = Store(tmp_path / "b" / "p.db")
    assert a.hmac("k") != b.hmac("k")
    assert len(a.hmac("k")) == 64


def test_secret_path_can_be_given(tmp_path):
    s = Store(tmp_path / "p.db", secret_path=tmp_path / "elsewhere")
    assert (tmp_path / "elsewhere").exists()
    s.close()


def test_wal_mode(store):
    assert store.db.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_schema_has_the_spec_tables(store):
    names = {r[0] for r in store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"units", "unit_keys", "visits", "alerts", "state"} <= names


def test_roundtrip(tmp_path):
    s = Store(tmp_path / "p.db")
    s.put_unit(unit(label="known", label_name="Neighbour's car", baseline=True))
    s.put_key("h1", KeyInfo(unit_id=1, kind="id", bits=48.0))
    s.put_key("h2", KeyInfo(unit_id=None, kind="id", bits=30.0, shared=True))
    s.put_visit(Visit(id=7, unit_id=1, start=1000.0, end=1300.0, n=5, max_rssi=-60, sum_rssi=-330.0))
    s.put_alert(Alert(id=3, unit_id=1, rule="R1", severity="alert", created=1300.0, details={"visit": 7}))
    s.set_state("armed", True)
    s.flush()
    s.close()

    snap = Store(tmp_path / "p.db").load()
    (u,) = snap.units.values()
    assert u.label == "known" and u.label_name == "Neighbour's car" and u.baseline
    assert u.id_types == {"Vendor device ID"} and u.hint == "3F2A" and u.mobility == "fixed"
    assert snap.keys["h1"] == KeyInfo(unit_id=1, kind="id", bits=48.0, shared=False)
    assert snap.keys["h2"].shared and snap.keys["h2"].unit_id is None
    (v,) = snap.visits
    assert (v.id, v.unit_id, v.start, v.end, v.n, v.max_rssi) == (7, 1, 1000.0, 1300.0, 5, -60)
    assert v.avg_rssi == pytest.approx(-66.0)
    (a,) = snap.alerts
    assert a.rule == "R1" and a.details == {"visit": 7} and not a.acked
    assert snap.state["armed"] is True
    assert snap.next_ids == {"unit": 2, "visit": 8, "alert": 4}


def test_upserts_replace(store):
    store.put_unit(unit())
    store.flush()
    store.put_unit(unit(last_seen=9999.0))
    store.flush()
    assert store.load().units[1].last_seen == 9999.0


def test_merge_moves_keys_visits_and_alerts(store):
    store.put_unit(unit(id=1))
    store.put_unit(unit(id=2))
    store.put_key("h1", KeyInfo(1, "id", 48.0))
    store.put_key("h2", KeyInfo(2, "id", 48.0))
    store.put_visit(Visit(id=1, unit_id=2, start=1.0, end=2.0, n=1, max_rssi=-70, sum_rssi=-70.0))
    store.put_alert(Alert(id=1, unit_id=2, rule="R2", severity="alert", created=2.0))
    store.flush()
    store.merge(keep=1, gone=2)
    store.flush()
    snap = store.load()
    assert set(snap.units) == {1}
    assert {k.unit_id for k in snap.keys.values()} == {1}
    assert snap.visits[0].unit_id == 1
    assert snap.alerts[0].unit_id == 1


def test_a_unit_merged_away_before_its_first_flush_is_never_written(store):
    store.put_unit(unit(id=1))
    store.put_unit(unit(id=2))
    store.merge(keep=1, gone=2)
    store.flush()
    assert set(store.load().units) == {1}


def test_writes_are_batched_at_least_30s_apart(store):
    store.put_unit(unit())
    assert store.maybe_flush(now=100.0)            # the first flush may happen at once
    store.put_unit(unit(last_seen=5000.0))
    assert not store.maybe_flush(now=100.0 + FLUSH_INTERVAL_S - 1)
    on_disk = lambda: store.db.execute("SELECT last_seen FROM units WHERE id=1").fetchone()[0]
    assert on_disk() == 2000.0
    assert store.maybe_flush(now=100.0 + FLUSH_INTERVAL_S)
    assert on_disk() == 5000.0
    assert FLUSH_INTERVAL_S >= 30


def test_nothing_to_write_is_not_a_flush(store):
    assert not store.maybe_flush(now=100.0)


def test_delete_visit(store):
    store.put_visit(Visit(id=1, unit_id=1, start=1.0, end=2.0, n=1, max_rssi=-70, sum_rssi=-70.0))
    store.flush()
    store.delete_visit(1)
    store.flush()
    assert store.load().visits == []


def test_retention(store):
    now = 400 * DAY
    store.put_unit(unit(id=1, last_seen=now - 91 * DAY))                    # stale, unlabelled: goes
    store.put_unit(unit(id=2, last_seen=now - 91 * DAY, label="known"))    # stale but labelled: stays
    store.put_unit(unit(id=3, last_seen=now - 89 * DAY))                    # recent: stays
    store.put_key("h1", KeyInfo(1, "id", 48.0))
    store.put_key("h3", KeyInfo(3, "id", 48.0))
    store.put_visit(Visit(id=1, unit_id=3, start=now - 181 * DAY, end=now - 181 * DAY, n=1, max_rssi=-70, sum_rssi=-70.0))
    store.put_visit(Visit(id=2, unit_id=3, start=now - 179 * DAY, end=now - 179 * DAY, n=1, max_rssi=-70, sum_rssi=-70.0))
    store.put_alert(Alert(id=1, unit_id=3, rule="R1", severity="alert", created=now - 181 * DAY))
    store.put_alert(Alert(id=2, unit_id=3, rule="R1", severity="alert", created=now - 179 * DAY))
    store.flush()
    gone = store.retention(now)
    assert gone == {1}
    snap = store.load()
    assert set(snap.units) == {2, 3}
    assert set(snap.keys) == {"h3"}
    assert [v.id for v in snap.visits] == [2]
    assert [a.id for a in snap.alerts] == [2]


def test_shared_keys_survive_retention(store):
    store.put_key("hs", KeyInfo(None, "id", 30.0, shared=True))
    store.flush()
    store.retention(10_000 * DAY)
    assert "hs" in store.load().keys


def test_raw_identifiers_never_reach_disk(tmp_path):
    """SPEC §6: write some, then grep the DB file's bytes for the raw values."""
    raw_values = ["TEST0001", "C0:FF:EE:00:00:01", "C0FFEE000001", "S39 ABCD LE"]
    s = Store(tmp_path / "p.db")
    s.put_unit(unit(hint="0001"))
    for i, v in enumerate(raw_values):
        s.put_key(s.hmac(f"id:test:serial:{v}"), KeyInfo(1, "id", 48.0))
    s.flush()
    s.db.execute("PRAGMA wal_checkpoint(FULL)")
    s.close()
    blob = b"".join(p.read_bytes() for p in tmp_path.iterdir() if p.is_file() and p.name != "secret")
    for v in raw_values:
        assert v.encode() not in blob
        assert v.lower().encode() not in blob
