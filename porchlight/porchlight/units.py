"""Units: one physical device each (SPEC §4.4).

Keys seen in the same ad, or from the same address within RADIO_WINDOW_S
(the same radio), belong to the same unit: a union-find over keys, persisted
as unit_keys. Weak keys (under 24 bits) can join a unit but never merge two
existing units, because short tokens collide in a busy neighbourhood.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .model import NO_MOBILITY_RANK, KeyInfo, Unit
from .resolver import CONFIDENCE_RANK, FieldTable, IdentityKey
from .store import Snapshot, Store

RADIO_WINDOW_S = 600.0
PARSER_MAJORITY_RANK = 3


@dataclass
class Observation:
    unit: Unit
    new_unit: bool = False
    merged: list = field(default_factory=list)   # ids of units folded into `unit`


class UnitBook:
    def __init__(self, table: FieldTable, store: Store, snapshot: Snapshot | None = None):
        self.table = table
        self.store = store
        snap = snapshot or Snapshot(next_ids={"unit": 1})
        self.units: dict[int, Unit] = dict(snap.units)
        self.keys: dict[str, KeyInfo] = dict(snap.keys)
        self._by_unit: dict[int, set[str]] = {}
        for h, info in self.keys.items():
            if info.unit_id is not None:
                self._by_unit.setdefault(info.unit_id, set()).add(h)
        self._next_id = snap.next_ids.get("unit", 1)
        self._radio: dict[str, tuple[int, float]] = {}   # addr -> (unit id, last seen)
        self._parsers: dict[int, set[str]] = {}          # unit id -> parsers seen (not persisted)

    def is_shared(self, key_hmac: str) -> bool:
        info = self.keys.get(key_hmac)
        return info is not None and info.shared

    def mark_shared(self, key_hmac: str, kind: str, bits: float) -> None:
        info = self.keys.get(key_hmac)
        if info is None:
            info = self.keys[key_hmac] = KeyInfo(unit_id=None, kind=kind, bits=bits)
        info.shared = True
        self.store.put_key(key_hmac, info)

    def observe(self, keys: list[tuple[IdentityKey, str]], addr: str, t: float, parsers: list[str]) -> Observation | None:
        """File one ad's keys. Returns None when the ad has no usable key."""
        keys = [(k, h) for k, h in keys if not self.is_shared(h)]
        if not keys:
            return None
        strong, weak = set(), []
        for k, h in keys:
            info = self.keys.get(h)
            if info is None or info.unit_id is None:
                continue
            if k.weak:
                weak.append(info.unit_id)
            else:
                strong.add(info.unit_id)
        radio = self._radio.get(addr)
        if radio and t - radio[1] <= RADIO_WINDOW_S and radio[0] in self.units:
            strong.add(radio[0])

        obs: Observation
        if strong:
            keep = min(strong, key=lambda uid: (self.units[uid].first_seen, uid))
            obs = Observation(self.units[keep])
            for gone in sorted(strong - {keep}):
                self._merge(keep, gone)
                obs.merged.append(gone)
        elif weak:
            # No merging on weak evidence: take the unit most of the weak keys
            # point at (latest seen on a tie), and leave the others alone.
            best = max(set(weak), key=lambda uid: (weak.count(uid), self.units[uid].last_seen))
            obs = Observation(self.units[best])
        else:
            obs = Observation(self._new_unit(t), new_unit=True)

        u = obs.unit
        for k, h in keys:
            info = self.keys.get(h)
            if info is None or info.unit_id is None:
                info = self.keys[h] = KeyInfo(unit_id=u.id, kind=k.kind, bits=k.bits)
                self._by_unit.setdefault(u.id, set()).add(h)
                self.store.put_key(h, info)
            if info.unit_id == u.id:
                self._absorb_key(u, k)
        self._parsers.setdefault(u.id, set()).update(p for p in parsers if p)
        if u.mobility_rank >= PARSER_MAJORITY_RANK:
            self._parser_fallback(u)
        u.last_seen = max(u.last_seen, t)
        self._radio[addr] = (u.id, t)
        self.store.put_unit(u)
        return obs

    def remove(self, unit_ids) -> None:
        for uid in unit_ids:
            self.units.pop(uid, None)
            self._parsers.pop(uid, None)
            for h in self._by_unit.pop(uid, set()):
                self.keys.pop(h, None)
        self._radio = {a: r for a, r in self._radio.items() if r[0] in self.units}

    def prune_radio(self, now: float) -> None:
        self._radio = {a: r for a, r in self._radio.items() if now - r[1] <= RADIO_WINDOW_S}

    # --- internals ---------------------------------------------------------

    def _new_unit(self, t: float) -> Unit:
        u = Unit(id=self._next_id, first_seen=t, last_seen=t)
        self._next_id += 1
        self.units[u.id] = u
        return u

    def _absorb_key(self, u: Unit, k: IdentityKey) -> None:
        if k.id_type:
            u.id_types.add(k.id_type)
        if not k.weak:
            u.weak = False
        if k.vendor and u.vendor is None:
            u.vendor, u.product = k.vendor, k.product
        # Mobility, and the vendor and product with it, come from the best-
        # confidence table row that knows the mobility.
        rank = CONFIDENCE_RANK.get(k.confidence, NO_MOBILITY_RANK)
        if k.mobility != "unknown" and rank < u.mobility_rank:
            u.mobility, u.mobility_rank = k.mobility, rank
            u.vendor, u.product = k.vendor or u.vendor, k.product or u.product
        if not u.hint or k.bits > u.hint_bits:
            u.hint, u.hint_bits = k.hint, k.bits

    def _parser_fallback(self, u: Unit) -> None:
        parsers = self._parsers.get(u.id, set())
        mobility = self.table.parser_mobility(parsers)
        if mobility != "unknown":
            u.mobility, u.mobility_rank = mobility, PARSER_MAJORITY_RANK
        if u.vendor is None:
            row = self.table.parser_row(parsers)
            if row:
                u.vendor, u.product = row.vendor, row.product

    def _merge(self, keep: int, gone: int) -> None:
        a, b = self.units[keep], self.units.pop(gone)
        a.first_seen = min(a.first_seen, b.first_seen)
        a.last_seen = max(a.last_seen, b.last_seen)
        a.id_types |= b.id_types
        a.weak = a.weak and b.weak
        a.baseline = a.baseline or b.baseline
        if a.label is None and b.label is not None:
            a.label, a.label_name = b.label, b.label_name
        if b.mobility_rank < a.mobility_rank:
            a.mobility, a.mobility_rank, a.vendor, a.product = b.mobility, b.mobility_rank, b.vendor, b.product
        if b.hint_bits > a.hint_bits:
            a.hint, a.hint_bits = b.hint, b.hint_bits
        for h in self._by_unit.pop(gone, set()):
            self.keys[h].unit_id = keep
            self._by_unit.setdefault(keep, set()).add(h)
        self._parsers.setdefault(keep, set()).update(self._parsers.pop(gone, set()))
        self._radio = {addr: (keep if uid == gone else uid, ts) for addr, (uid, ts) in self._radio.items()}
        self.store.merge(keep=keep, gone=gone)
        self.store.put_unit(a)
