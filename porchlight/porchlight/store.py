"""SQLite persistence (SPEC §4.10).

Identity keys are stored only as HMAC-SHA256(local secret, key); raw values
never touch disk. Times are UTC epoch seconds. While running, the in-memory
model is the source of truth: changes are queued here and written in one
transaction at most every FLUSH_INTERVAL_S, to spare the SD card.
"""

from __future__ import annotations

import hashlib
import hmac as hmac_mod
import json
import os
import secrets
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from .model import Alert, KeyInfo, Unit, Visit

SCHEMA_VERSION = 1
FLUSH_INTERVAL_S = 30.0
VISIT_RETENTION_S = 180 * 86400.0
UNIT_RETENTION_S = 90 * 86400.0

SCHEMA = """
CREATE TABLE IF NOT EXISTS units (
    id INTEGER PRIMARY KEY, vendor TEXT, product TEXT, id_types TEXT, mobility TEXT,
    weak INTEGER, first_seen REAL, last_seen REAL, label TEXT, label_name TEXT,
    hint TEXT, baseline INTEGER, mobility_rank INTEGER);
CREATE TABLE IF NOT EXISTS unit_keys (
    key_hmac TEXT PRIMARY KEY, unit_id INTEGER, kind TEXT, bits REAL, shared INTEGER);
CREATE INDEX IF NOT EXISTS unit_keys_unit ON unit_keys(unit_id);
CREATE TABLE IF NOT EXISTS visits (
    id INTEGER PRIMARY KEY, unit_id INTEGER, start REAL, end REAL, n INTEGER,
    max_rssi INTEGER, avg_rssi REAL);
CREATE INDEX IF NOT EXISTS visits_unit ON visits(unit_id, start);
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY, unit_id INTEGER, rule TEXT, severity TEXT, created REAL,
    acked INTEGER, details_json TEXT);
CREATE TABLE IF NOT EXISTS state (k TEXT PRIMARY KEY, v TEXT);
"""


@dataclass
class Snapshot:
    units: dict = field(default_factory=dict)       # id -> Unit
    keys: dict = field(default_factory=dict)        # hmac -> KeyInfo
    visits: list = field(default_factory=list)      # Visit, by start
    alerts: list = field(default_factory=list)      # Alert, by id
    state: dict = field(default_factory=dict)
    next_ids: dict = field(default_factory=dict)


def _load_secret(path: Path) -> bytes:
    if path.exists():
        return path.read_bytes()
    path.parent.mkdir(parents=True, exist_ok=True)
    value = secrets.token_bytes(32)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(value)
    return value


class Store:
    def __init__(self, path: str | Path, secret_path: str | Path | None = None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._secret = _load_secret(Path(secret_path) if secret_path else self.path.parent / "secret")
        self.db = sqlite3.connect(self.path)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=NORMAL")
        self.db.executescript(SCHEMA)
        self.db.execute("INSERT OR IGNORE INTO state(k, v) VALUES ('schema_version', ?)", (json.dumps(SCHEMA_VERSION),))
        self.db.commit()
        self._units: dict[int, Unit] = {}
        self._keys: dict[str, KeyInfo] = {}
        self._visits: dict[int, Visit] = {}
        self._alerts: dict[int, Alert] = {}
        self._state: dict[str, object] = {}
        self._merges: list[tuple[int, int]] = []
        self._deleted_visits: set[int] = set()
        self._last_flush: float | None = None

    def close(self) -> None:
        self.flush()
        self.db.close()

    def hmac(self, key: str) -> str:
        return hmac_mod.new(self._secret, key.encode(), hashlib.sha256).hexdigest()

    # --- queueing ------------------------------------------------------------

    def put_unit(self, u: Unit) -> None:
        self._units[u.id] = u

    def put_key(self, key_hmac: str, info: KeyInfo) -> None:
        self._keys[key_hmac] = info

    def put_visit(self, v: Visit) -> None:
        self._deleted_visits.discard(v.id)
        self._visits[v.id] = v

    def delete_visit(self, visit_id: int) -> None:
        self._visits.pop(visit_id, None)
        self._deleted_visits.add(visit_id)

    def put_alert(self, a: Alert) -> None:
        self._alerts[a.id] = a

    def set_state(self, k: str, v) -> None:
        self._state[k] = v

    def merge(self, keep: int, gone: int) -> None:
        """Unit `gone` was merged into `keep`: move its rows, delete it."""
        self._units.pop(gone, None)
        self._merges.append((keep, gone))

    @property
    def pending(self) -> bool:
        return bool(self._units or self._keys or self._visits or self._alerts or self._state
                     or self._merges or self._deleted_visits)

    # --- writing -----------------------------------------------------------------

    def maybe_flush(self, now: float) -> bool:
        if not self.pending:
            return False
        if self._last_flush is not None and now - self._last_flush < FLUSH_INTERVAL_S:
            return False
        self.flush()
        self._last_flush = now
        return True

    def flush(self) -> None:
        if not self.pending:
            return
        with self.db:
            self.db.executemany(
                "INSERT OR REPLACE INTO units VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                [(u.id, u.vendor, u.product, ",".join(sorted(u.id_types)), u.mobility, int(u.weak),
                  u.first_seen, u.last_seen, u.label, u.label_name, u.hint, int(u.baseline), u.mobility_rank)
                 for u in self._units.values()])
            for keep, gone in self._merges:
                for table in ("unit_keys", "visits", "alerts"):
                    self.db.execute(f"UPDATE {table} SET unit_id=? WHERE unit_id=?", (keep, gone))
                self.db.execute("DELETE FROM units WHERE id=?", (gone,))
            self.db.executemany(
                "INSERT OR REPLACE INTO unit_keys VALUES (?,?,?,?,?)",
                [(h, k.unit_id, k.kind, k.bits, int(k.shared)) for h, k in self._keys.items()])
            self.db.executemany(
                "INSERT OR REPLACE INTO visits VALUES (?,?,?,?,?,?,?)",
                [(v.id, v.unit_id, v.start, v.end, v.n, v.max_rssi, v.avg_rssi) for v in self._visits.values()])
            self.db.executemany("DELETE FROM visits WHERE id=?", [(i,) for i in self._deleted_visits])
            self.db.executemany(
                "INSERT OR REPLACE INTO alerts VALUES (?,?,?,?,?,?,?)",
                [(a.id, a.unit_id, a.rule, a.severity, a.created, int(a.acked), json.dumps(a.details))
                 for a in self._alerts.values()])
            self.db.executemany(
                "INSERT OR REPLACE INTO state VALUES (?,?)",
                [(k, json.dumps(v)) for k, v in self._state.items()])
        self._units.clear()
        self._keys.clear()
        self._visits.clear()
        self._alerts.clear()
        self._state.clear()
        self._merges.clear()
        self._deleted_visits.clear()

    def retention(self, now: float) -> set[int]:
        """Drop visits and alerts older than 180 days and unlabelled units not
        seen for 90 days (with their keys, visits and alerts). Returns the
        deleted unit ids."""
        self.flush()
        cutoff_units = now - UNIT_RETENTION_S
        cutoff_rows = now - VISIT_RETENTION_S
        with self.db:
            gone = {r[0] for r in self.db.execute(
                "SELECT id FROM units WHERE label IS NULL AND last_seen < ?", (cutoff_units,))}
            for uid in gone:
                for table in ("unit_keys", "visits", "alerts"):
                    self.db.execute(f"DELETE FROM {table} WHERE unit_id=?", (uid,))
                self.db.execute("DELETE FROM units WHERE id=?", (uid,))
            self.db.execute("DELETE FROM visits WHERE end < ?", (cutoff_rows,))
            self.db.execute("DELETE FROM alerts WHERE created < ?", (cutoff_rows,))
        return gone

    # --- reading -------------------------------------------------------------------

    def load(self) -> Snapshot:
        self.flush()
        snap = Snapshot()
        for r in self.db.execute("SELECT * FROM units"):
            (uid, vendor, product, id_types, mobility, weak, first, last, label, label_name, hint, baseline,
             mobility_rank) = r
            snap.units[uid] = Unit(
                id=uid, vendor=vendor, product=product, id_types=set(filter(None, (id_types or "").split(","))),
                mobility=mobility or "unknown", weak=bool(weak), first_seen=first, last_seen=last, label=label,
                label_name=label_name or "", hint=hint or "", baseline=bool(baseline), mobility_rank=mobility_rank)
        for h, uid, kind, bits, shared in self.db.execute("SELECT * FROM unit_keys"):
            snap.keys[h] = KeyInfo(unit_id=uid, kind=kind, bits=bits, shared=bool(shared))
            u = snap.units.get(uid)
            if u is not None and not shared:
                u.hint_bits = max(u.hint_bits, bits)
        for vid, uid, start, end, n, max_rssi, avg_rssi in self.db.execute("SELECT * FROM visits ORDER BY start"):
            snap.visits.append(Visit(id=vid, unit_id=uid, start=start, end=end, n=n, max_rssi=max_rssi,
                                     sum_rssi=avg_rssi * n))
        for aid, uid, rule, severity, created, acked, details in self.db.execute("SELECT * FROM alerts ORDER BY id"):
            snap.alerts.append(Alert(id=aid, unit_id=uid, rule=rule, severity=severity, created=created,
                                     acked=bool(acked), details=json.loads(details or "{}")))
        for k, v in self.db.execute("SELECT k, v FROM state"):
            snap.state[k] = json.loads(v)

        def next_id(table):
            return (self.db.execute(f"SELECT MAX(id) FROM {table}").fetchone()[0] or 0) + 1

        snap.next_ids = {"unit": next_id("units"), "visit": next_id("visits"), "alert": next_id("alerts")}
        return snap
