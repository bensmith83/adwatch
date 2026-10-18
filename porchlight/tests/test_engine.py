import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from porchlight.config import Config
from porchlight.engine import Engine
from porchlight.resolver import FieldTable
from porchlight.store import Store

TZ = ZoneInfo("UTC")
DAY = 86400.0
T0 = datetime(2026, 10, 19, 12, 0, tzinfo=TZ).timestamp()

TABLE = FieldTable.from_dict({
    "fields": [
        {"source": "meta", "parser": "watch", "key": "serial", "id_type": "Serial number", "confidence": "high",
         "vendor": "Acme", "product": "Watch", "mobility": "personal"},
        {"source": "meta", "parser": "speaker", "key": "device_id", "id_type": "Vendor device ID",
         "confidence": "high", "vendor": "Acme", "product": "Speaker", "mobility": "fixed"},
        {"source": "meta", "parser": "fleet", "key": "id", "id_type": "Vendor device ID",
         "confidence": "high", "vendor": "Acme", "product": "Fleet tag", "mobility": "in_transit"},
    ],
    "name_families": [], "unreliable_parsers": [],
    "rules": {"weak_bits": 24, "shared_if_concurrent_addresses": 3,
              "name_token_regex": "[0-9A-Fa-f]{4,}|\\d{3,}"},
})


def ad(t, addr="40:00:00:00:00:01", rssi=-60, name=None):
    return {"t": int(t * 1000), "addr": addr, "atype": "random", "rssi": rssi, "mfr": None, "svc": {},
            "uuids": [], "name": name, "tx": None}


def watch(serial="TEST0001"):
    return [{"parser": "watch", "beaconType": "watch", "deviceClass": "wearable", "stableKey": None,
             "metadata": {"serial": serial}}]


def speaker(dev="c0ffee000001"):
    return [{"parser": "speaker", "beaconType": "speaker", "deviceClass": "speaker", "stableKey": None,
             "metadata": {"device_id": dev}}]


def config(**over):
    c = Config()
    c.learning.learning_days = over.pop("learning_days", 0)
    for k, v in over.items():
        section, key = k.split("__")
        setattr(getattr(c, section), key, v)
    return c


class Rig:
    def __init__(self, tmp_path, cfg=None, now=T0):
        self.tmp_path = tmp_path
        self.cfg = cfg or config()
        self.store = Store(tmp_path / "p.db")
        self.engine = Engine(self.cfg, TABLE, self.store, now=now, tz=TZ)
        self.pushed = []
        self.entries = []
        self.engine.on_alert.append(lambda a, u, pushed: (self.entries.append(a), pushed and self.pushed.append(a)))

    def stay(self, results, start, minutes, every=10.0, addr="40:00:00:00:00:01", rssi=-60):
        t = start
        while t <= start + minutes * 60:
            self.engine.ingest(ad(t, addr=addr, rssi=rssi), results)
            self.engine.tick(t)
            t += every
        return t

    def reopen(self, now):
        self.store.close()
        self.store = Store(self.tmp_path / "p.db")
        self.engine = Engine(self.cfg, TABLE, self.store, now=now, tz=TZ)
        self.engine.on_alert.append(lambda a, u, pushed: (self.entries.append(a), pushed and self.pushed.append(a)))


@pytest.fixture
def rig(tmp_path):
    r = Rig(tmp_path)
    yield r
    r.store.close()


def test_a_sighting_makes_a_unit_and_a_visit(rig):
    rig.engine.ingest(ad(T0), watch())
    (u,) = rig.engine.units.units.values()
    assert u.product == "Watch" and u.mobility == "personal" and u.hint == "0001"
    assert rig.engine.visits.open[u.id].n == 1


def test_ads_with_no_identity_only_count_as_anonymous(rig):
    rig.engine.ingest(ad(T0, addr="40:00:00:00:00:02"), [])
    rig.engine.ingest(ad(T0 + 1, addr="40:00:00:00:00:03"), [])
    assert rig.engine.units.units == {}
    assert rig.engine.anonymous_nearby(T0 + 2) == 2
    assert rig.engine.anonymous_nearby(T0 + 120) == 0


def test_a_value_on_three_radios_at_once_is_shared_and_ignored(rig):
    fleet = [{"parser": "fleet", "beaconType": "x", "deviceClass": "x", "stableKey": None, "metadata": {"id": "TEST9999"}}]
    for i in range(3):
        rig.engine.ingest(ad(T0 + i, addr=f"40:00:00:00:00:1{i}"), fleet)
    rig.engine.ingest(ad(T0 + 10, addr="40:00:00:00:00:19"), fleet)
    rig.store.flush()
    keys = rig.store.load().keys
    assert any(k.shared for k in keys.values())
    # the radios seen before the verdict may have units; nothing new is made from the shared value
    before = len(rig.engine.units.units)
    rig.engine.ingest(ad(T0 + 20, addr="40:00:00:00:00:29"), fleet)
    assert len(rig.engine.units.units) == before


def test_r1_end_to_end(rig):
    rig.stay(watch(), T0, minutes=11)
    (a,) = [e for e in rig.entries if e.rule == "R1"]
    assert a.severity == "alert"
    assert rig.pushed == [a]
    assert "Watch" in a.details["message"] and "…0001" in a.details["message"]


def test_nothing_is_pushed_while_learning(tmp_path):
    rig = Rig(tmp_path, config(learning_days=7))
    rig.stay(watch(), T0, minutes=11)
    (a,) = [e for e in rig.entries if e.rule == "R1"]
    assert a.details["learning"] is True
    assert rig.pushed == []
    state = rig.engine.state()
    assert state["learning"]["active"] is True
    assert [w["id"] for w in state["would_have"]] == [a.id]
    assert state["alerts"] == []


def test_learning_ends_with_a_baseline(tmp_path):
    rig = Rig(tmp_path, config(learning_days=7))
    for d in range(3):
        rig.stay(watch(), T0 + d * DAY, minutes=1)
    rig.stay(speaker(), T0, minutes=1, addr="40:00:00:00:00:05")
    rig.engine.tick(T0 + 7 * DAY)
    assert all(u.baseline for u in rig.engine.units.units.values())
    assert rig.engine.state()["learning"]["active"] is False


def test_household_and_ignore_never_alert(rig):
    rig.engine.ingest(ad(T0), watch())
    (u,) = rig.engine.units.units.values()
    rig.engine.label(u.id, "household", "My watch")
    rig.stay(watch(), T0, minutes=30)
    assert rig.entries == []


def test_ack_with_a_label_from_the_alert(rig):
    rig.stay(watch(), T0, minutes=11)
    (a,) = rig.entries
    rig.engine.ack(a.id, label="known", name="Postie")
    u = rig.engine.units.units[a.unit_id]
    assert u.label == "known" and u.label_name == "Postie"
    assert rig.engine.alerts.alerts[a.id].acked
    assert rig.engine.state()["alerts"] == []


def test_labelling_a_unit_acks_its_open_alerts(rig):
    rig.stay(watch(), T0, minutes=11)
    (a,) = rig.entries
    rig.engine.label(a.unit_id, "ignore")
    assert rig.engine.alerts.alerts[a.id].acked


def test_bad_labels_are_rejected(rig):
    rig.engine.ingest(ad(T0), watch())
    (u,) = rig.engine.units.units.values()
    with pytest.raises(ValueError):
        rig.engine.label(u.id, "friend")


def test_presence_mode_arms_when_the_household_watch_leaves(tmp_path):
    rig = Rig(tmp_path, config(arming__mode="presence"))
    rig.engine.ingest(ad(T0), watch())
    (u,) = rig.engine.units.units.values()
    rig.engine.label(u.id, "household", "My watch")
    end = rig.stay(watch(), T0, minutes=5)
    assert rig.engine.arming.armed is False
    rig.engine.tick(end + 14 * 60)
    assert rig.engine.arming.armed is False
    rig.engine.tick(end - 10 + 15 * 60)
    assert rig.engine.arming.armed is True
    rig.engine.ingest(ad(end + 3600), watch())
    assert rig.engine.arming.armed is False


def test_weak_household_units_are_not_presence_keys(tmp_path):
    rig = Rig(tmp_path, config(arming__mode="presence"))
    rig.engine.ingest(ad(T0), watch(serial="ABCD"))      # 16 bits: weak
    (u,) = rig.engine.units.units.values()
    assert u.weak
    rig.engine.label(u.id, "household")
    rig.engine.tick(T0 + 20 * 60)
    rig.engine.ingest(ad(T0 + 20 * 60), watch(serial="ABCD"))
    assert rig.engine.arming.armed is True
    assert rig.engine.state()["presence_keys"] == []


def test_arming_changes_are_announced(tmp_path):
    rig = Rig(tmp_path, config(arming__mode="manual"))
    seen = []
    rig.engine.on_arming.append(seen.append)
    rig.engine.arm(True)
    assert seen == [True]
    assert rig.engine.state()["armed"]["armed"] is True


def test_r3_when_armed(tmp_path):
    rig = Rig(tmp_path, config(arming__mode="always"))
    rig.stay(watch(), T0, minutes=2)
    assert [e.rule for e in rig.entries] == ["R3"]


def test_state_survives_a_restart(rig):
    rig.stay(watch(), T0, minutes=11)
    (a,) = rig.entries
    rig.engine.label(a.unit_id, "known", "Postie")
    rig.engine.arm(True)
    rig.engine.shutdown()
    rig.reopen(T0 + 3600)
    u = rig.engine.units.units[a.unit_id]
    assert u.label == "known" and u.label_name == "Postie"
    assert rig.engine.alerts.alerts[a.id].acked
    assert rig.engine.arming.armed is True
    rig.engine.ingest(ad(T0 + 3600, addr="40:00:00:00:00:44"), watch())
    assert len(rig.engine.units.units) == 1, "the same serial is the same unit after a restart"


def test_merges_move_visits_and_alerts(rig):
    rig.stay(watch("TEST0001"), T0, minutes=11, addr="40:00:00:00:00:01")
    rig.stay(watch("TEST0002"), T0 + DAY, minutes=1, addr="40:00:00:00:00:02")
    assert len(rig.engine.units.units) == 2
    both = watch("TEST0001") + watch("TEST0002")
    rig.engine.ingest(ad(T0 + 2 * DAY, addr="40:00:00:00:00:03"), both)
    (u,) = rig.engine.units.units.values()
    assert all(a.unit_id == u.id for a in rig.engine.alerts.alerts.values())
    assert len(rig.engine.visits.history.get(u.id, [])) == 2


def test_the_page_state_masks_identifiers(rig):
    rig.stay(watch("TEST0001"), T0, minutes=11)
    text = json.dumps(rig.engine.state()) + json.dumps(rig.engine.units_list())
    assert "TEST0001" not in text and "40:00:00:00:00:01" not in text
    assert "0001" in text
    near = rig.engine.state()["near"]
    assert near[0]["product"] == "Watch" and near[0]["mobility"] == "personal" and near[0]["hint"] == "0001"
    assert near[0]["dwell_s"] >= 600


def test_no_raw_identifiers_on_disk_after_a_run(rig):
    rig.stay(watch("TEST0001"), T0, minutes=11, addr="C0:FF:EE:00:00:01")
    rig.stay(speaker("c0ffee000002"), T0, minutes=2, addr="C0:FF:EE:00:00:02")
    rig.engine.shutdown()
    rig.store.db.execute("PRAGMA wal_checkpoint(FULL)")
    blob = b"".join(p.read_bytes() for p in rig.tmp_path.iterdir() if p.is_file() and p.name != "secret")
    for raw in ("TEST0001", "c0ffee000002", "C0:FF:EE:00:00:01", "C0FFEE000001", "C0:FF:EE:00:00:02"):
        assert raw.encode() not in blob and raw.lower().encode() not in blob


def test_retention_runs_daily(rig):
    rig.engine.ingest(ad(T0), watch())
    rig.engine.tick(T0 + 1)
    rig.engine.tick(T0 + 91 * DAY)
    assert rig.engine.units.units == {}


def test_relearn(tmp_path):
    rig = Rig(tmp_path, config(learning_days=7))
    rig.stay(speaker(), T0, minutes=1)
    rig.engine.tick(T0 + 7 * DAY)
    (u,) = rig.engine.units.units.values()
    assert u.baseline
    rig.engine.label(u.id, "known")
    rig.engine.relearn()
    assert not u.baseline and u.label == "known"
    assert rig.engine.state()["learning"]["active"] is True


def test_the_about_box_shows_the_parser_count_and_commit(rig):
    rig.engine.info = {"parsers": "12", "commit": "abc123"}
    about = rig.engine.state()["about"]
    assert (about["parsers"], about["commit"]) == ("12", "abc123")


def test_ads_per_second(rig):
    for i in range(100):
        rig.engine.ingest(ad(T0 + i * 0.1), [])
    rig.engine.tick(T0 + 10)
    assert rig.engine.state()["about"]["ads_per_s"] == pytest.approx(10, rel=0.2)
