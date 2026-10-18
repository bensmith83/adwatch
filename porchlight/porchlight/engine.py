"""The pipeline from parsed ads to alerts, without I/O beyond the store.

ingest() takes one ad and its parser results; tick() does the time-driven
work (closing visits, checkpoints, arming, learning, retention, flushing).
Both run on the ad's own clock, so live scanning and replay at any speed
behave the same.
"""

from __future__ import annotations

import logging
from collections import OrderedDict, deque
from datetime import tzinfo

from .arming import Arming
from .config import Config
from .learning import Learning
from .model import LABELS, Alert, Unit, Visit
from .resolver import FieldTable, Resolver, SharedGuard
from .rules import AlertBook, Rules, describe
from .sidecar import ParseCache
from .store import VISIT_RETENTION_S, Store
from .timeutil import local_zone
from .units import UnitBook
from .visits import VisitTracker

log = logging.getLogger(__name__)

DAY_S = 86400.0
ANON_WINDOW_S = 60.0
RSSI_TRACE_S = 60.0
RULES = ("R1", "R2", "R3", "R4")
RESOLVE_CACHE = 4096


class StateView:
    """The persisted `state` table: reads from memory, writes through the store."""

    def __init__(self, store: Store, initial: dict):
        self.store = store
        self._d = dict(initial)

    def get(self, k, default=None):
        return self._d.get(k, default)

    def set_state(self, k, v) -> None:
        self._d[k] = v
        self.store.set_state(k, v)


class Engine:
    def __init__(self, cfg: Config, table: FieldTable, store: Store, now: float, tz: tzinfo | None = None):
        self.cfg = cfg
        self.table = table
        self.store = store
        self.tz = tz or local_zone()
        self.floor = cfg.presence.rssi_floor
        snap = store.load()
        self.state_view = StateView(store, snap.state)
        self.resolver = Resolver(table, cfg.identity.include_low_confidence)
        self.units = UnitBook(table, store, snap)
        self.visits = VisitTracker(cfg.presence.visit_gap_minutes * 60, self.floor, store, snap.next_ids.get("visit", 1))
        self.visits.restore(snap, now)
        self.guard = SharedGuard(table.shared_threshold, 60.0, {h for h, k in snap.keys.items() if k.shared})
        self.alerts = AlertBook(snap.alerts, snap.next_ids.get("alert", 1))
        self.rules = Rules(cfg.rules, self.floor, self.tz)
        self.arming = Arming(cfg.arming, self.tz, self.state_view, now)
        self.learning = Learning(cfg.learning.learning_days, self.state_view, now)
        self.on_alert: list = []     # callback(alert, unit, pushed)
        self.on_arming: list = []    # callback(armed)
        self.info: dict = {}         # ble-parse --info, for the About box
        self.now = now
        self.started = now
        self._armed = self.arming.armed
        self._anon: dict[str, float] = {}
        self._resolved: OrderedDict[str, list] = OrderedDict()
        self._ads = 0
        self._rate_mark = (now, 0)
        self.ads_per_s = 0.0
        self._last_retention: float | None = None
        self._rssi: dict[int, deque] = {}   # unit id -> recent (t, rssi), for calibration

    # --- pipeline ------------------------------------------------------------

    def ingest(self, ad: dict, results: list[dict]) -> None:
        t = ad["t"] / 1000.0
        self.now = max(self.now, t)
        self._ads += 1
        addr = ad["addr"]
        usable = []
        for k, h in self._resolve(ad, results):
            if k.payload and self.guard.observe(h, addr, t):
                if not self.units.is_shared(h):
                    self.units.mark_shared(h, k.kind, k.bits)
                    log.info("a %s value is broadcast by %d+ radios: treating it as shared", k.parser,
                             self.guard.threshold)
                continue
            usable.append((k, h))
        obs = self.units.observe(usable, addr, t, [r.get("parser", "") for r in results])
        if obs is None:
            self._anon[addr] = t
            return
        u = obs.unit
        for gone in obs.merged:
            self.visits.merge(u.id, gone)
            for a in self.alerts.reassign(u.id, gone):
                self.store.put_alert(a)
        rssi = int(ad.get("rssi") or -127)
        v, _ = self.visits.sight(u.id, t, rssi)
        trace = self._rssi.setdefault(u.id, deque())
        trace.append((t, rssi))
        while trace and trace[0][0] < t - RSSI_TRACE_S:
            trace.popleft()
        if u.label == "household" and not u.weak and rssi >= self.floor:
            self.arming.household_near(t)
            self._announce_arming()
        self._evaluate(u, v, t)

    def _resolve(self, ad: dict, results: list[dict]) -> list:
        ck = ParseCache.key(ad)
        hit = self._resolved.get(ck)
        if hit is not None:
            self._resolved.move_to_end(ck)
            return hit
        pairs = [(k, self.store.hmac(k.key)) for k in self.resolver.resolve(ad, results)]
        self._resolved[ck] = pairs
        while len(self._resolved) > RESOLVE_CACHE:
            self._resolved.popitem(last=False)
        return pairs

    def _evaluate(self, u: Unit, v: Visit, t: float) -> None:
        fires = self.rules.evaluate(u, v, self.visits.history.get(u.id, []), armed=self.arming.armed, now=t,
                                    alerts=self.alerts)
        learning = self.learning.active(t)
        for f in fires:
            f.details["learning"] = learning
            a = self.alerts.add(u.id, f, created=t)
            self.store.put_alert(a)
            pushed = not learning and a.severity != "info"
            for cb in self.on_alert:
                cb(a, u, pushed)

    def tick(self, now: float) -> None:
        self.now = max(self.now, now)
        now = self.now
        self.visits.sweep(now)
        self.visits.checkpoint(now)
        self.guard.prune(now)
        self.units.prune_radio(now)
        self._anon = {a: t for a, t in self._anon.items() if now - t <= ANON_WINDOW_S}
        self._rssi = {uid: tr for uid, tr in self._rssi.items() if uid in self.visits.open}
        if self.learning.due(now):
            chosen = self.learning.finish(self.units.units, self.visits.history, self.visits.open, self.floor, self.tz)
            for uid in chosen:
                self.store.put_unit(self.units.units[uid])
            log.info("learning finished: %d units baselined", len(chosen))
        self.arming.update(now)
        self._announce_arming()
        if self._last_retention is None or now - self._last_retention >= DAY_S:
            self._retention(now)
        mark_t, mark_n = self._rate_mark
        if now - mark_t >= 5:
            self.ads_per_s = (self._ads - mark_n) / (now - mark_t)
            self._rate_mark = (now, self._ads)
        self.store.maybe_flush(now)

    def _retention(self, now: float) -> None:
        self._last_retention = now
        gone = self.store.retention(now)
        if gone:
            self.units.remove(gone)
            self.visits.remove(gone)
            self.alerts.remove_units(gone)
            log.info("retention: forgot %d unlabelled units", len(gone))
        self.visits.prune(now - VISIT_RETENTION_S)
        self.alerts.prune(now - VISIT_RETENTION_S)

    def _announce_arming(self) -> None:
        if self.arming.armed != self._armed:
            self._armed = self.arming.armed
            log.info("%s", "armed" if self._armed else "disarmed")
            for cb in self.on_arming:
                cb(self._armed)

    def shutdown(self) -> None:
        self.visits.checkpoint(self.now, force=True)
        self.store.flush()

    # --- actions from the page ---------------------------------------------

    def label(self, unit_id: int, label: str | None, name: str = "") -> Unit:
        if label is not None and label not in LABELS:
            raise ValueError(f"label must be one of {', '.join(LABELS)} or empty")
        u = self.units.units[unit_id]
        u.label = label
        u.label_name = (name or "").strip()[:80] if label else ""
        self.store.put_unit(u)
        if label:
            for a in self.alerts.for_unit(unit_id):
                if not a.acked:
                    a.acked = True
                    self.store.put_alert(a)
        self.store.flush()
        return u

    def ack(self, alert_id: int, label: str | None = None, name: str = "") -> Alert:
        a = self.alerts.alerts[alert_id]
        a.acked = True
        self.store.put_alert(a)
        if label:
            self.label(a.unit_id, label, name)
        self.store.flush()
        return a

    def arm(self, armed: bool) -> None:
        self.arming.set(armed, self.now)
        self._announce_arming()
        self.store.flush()

    def clear_override(self) -> None:
        self.arming.clear_override()
        self.arming.update(self.now)
        self._announce_arming()
        self.store.flush()

    def relearn(self) -> None:
        self.learning.relearn(self.units.units, self.now)
        for u in self.units.units.values():
            self.store.put_unit(u)
        self.store.flush()

    # --- views (identifiers masked: vendor, product, ID type, 4-char hint) ---

    def anonymous_nearby(self, now: float | None = None) -> int:
        now = self.now if now is None else now
        return sum(1 for t in self._anon.values() if now - t <= ANON_WINDOW_S)

    def unit_view(self, u: Unit) -> dict:
        return {"id": u.id, "vendor": u.vendor, "product": u.product, "id_types": sorted(u.id_types),
                "mobility": u.mobility, "weak": u.weak, "first_seen": u.first_seen, "last_seen": u.last_seen,
                "label": u.label, "label_name": u.label_name, "hint": u.hint, "baseline": u.baseline,
                "known": u.known, "description": describe(u)}

    def alert_view(self, a: Alert) -> dict:
        u = self.units.units.get(a.unit_id)
        return {"id": a.id, "unit_id": a.unit_id, "rule": a.rule, "severity": a.severity, "created": a.created,
                "acked": a.acked, "title": a.details.get("title", a.rule), "message": a.details.get("message", ""),
                "learning": bool(a.details.get("learning")), "weak": bool(a.details.get("weak")),
                "unit": self.unit_view(u) if u else None}

    @staticmethod
    def visit_view(v: Visit) -> dict:
        return {"id": v.id, "start": v.start, "end": v.end, "n": v.n, "max_rssi": v.max_rssi,
                "avg_rssi": round(v.avg_rssi, 1)}

    def near_now(self) -> list[dict]:
        out = []
        for uid, v in self.visits.open.items():
            u = self.units.units.get(uid)
            if u is None:
                continue
            out.append(dict(self.unit_view(u), dwell_s=round(v.duration), rssi=v.last_rssi, max_rssi=v.max_rssi,
                            near=v.max_rssi >= self.floor, since=v.start, seen=v.end))
        out.sort(key=lambda d: (not d["near"], -d["rssi"]))
        return out

    def state(self) -> dict:
        alerts = sorted(self.alerts.alerts.values(), key=lambda a: -a.created)
        views = [self.alert_view(a) for a in alerts[:500]]
        return {
            "now": self.now,
            "armed": self.arming.status(),
            "learning": self.learning.status(self.now),
            "alerts": [a for a in views if not a["acked"] and not a["learning"] and a["severity"] != "info"],
            "info": [a for a in views if not a["acked"] and not a["learning"] and a["severity"] == "info"][:50],
            "would_have": [a for a in views if a["learning"]][:100],
            "near": self.near_now(),
            "presence_keys": [self.unit_view(u) for u in self.units.units.values()
                              if u.label == "household" and not u.weak],
            "rule_counts": self.rule_counts(),
            "about": {"parsers": self.info.get("parsers"), "commit": self.info.get("commit"),
                      "uptime_s": round(self.now - self.started), "ads_per_s": round(self.ads_per_s, 1),
                      "anonymous_nearby": self.anonymous_nearby(), "units": len(self.units.units)},
        }

    def rule_counts(self) -> dict:
        """Entries per rule: pushed by severity, info, and would-have (learning)."""
        counts = {r: {"alert": 0, "warn": 0, "info": 0, "would_have": 0} for r in RULES}
        for a in self.alerts.alerts.values():
            c = counts.setdefault(a.rule, {"alert": 0, "warn": 0, "info": 0, "would_have": 0})
            c["would_have" if a.details.get("learning") else a.severity] += 1
        return counts

    def rssi_trace(self, unit_id: int) -> dict | None:
        """The last minute of RSSI for one unit: walk to the curb wearing your
        watch and read the number."""
        u = self.units.units.get(unit_id)
        if u is None:
            return None
        samples = list(self._rssi.get(unit_id, ())) if unit_id in self.visits.open else []
        values = [r for _, r in samples]
        rssi = values[-1] if values else None
        return {"unit": self.unit_view(u), "floor": self.floor, "rssi": rssi,
                "min": min(values) if values else None, "max": max(values) if values else None,
                "near": rssi is not None and rssi >= self.floor, "samples": samples}

    def units_list(self, q: str = "", limit: int = 200) -> list[dict]:
        q = q.strip().lower()
        out = []
        for u in sorted(self.units.units.values(), key=lambda u: -u.last_seen):
            view = self.unit_view(u)
            hay = " ".join(str(view[k] or "") for k in ("vendor", "product", "label", "label_name", "hint", "mobility"))
            if q and q not in (hay + " " + " ".join(view["id_types"])).lower():
                continue
            out.append(view)
            if len(out) >= limit:
                break
        return out

    def unit_detail(self, unit_id: int) -> dict | None:
        u = self.units.units.get(unit_id)
        if u is None:
            return None
        visits = list(self.visits.history.get(unit_id, []))
        if unit_id in self.visits.open:
            visits.append(self.visits.open[unit_id])
        visits.sort(key=lambda v: -v.start)
        return dict(self.unit_view(u), visits=[self.visit_view(v) for v in visits[:100]],
                    alerts=[self.alert_view(a) for a in sorted(self.alerts.for_unit(unit_id), key=lambda a: -a.created)])
