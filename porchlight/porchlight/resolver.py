"""From one parsed advertisement to identity keys (SPEC §4.3, §9, §10).

The value rules here (bits, junk, bad MACs) are the ones the fields table
was built with, so a value counts here exactly when it counted there.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

CONFIDENCE_RANK = {"high": 0, "medium": 1, "low": 2}
MAC_BITS = 48.0

_ALNUM = re.compile(r"[0-9A-Za-z]+")
_HEX = re.compile(r"[0-9A-Fa-f]+")
_JUNK = re.compile(r"^[0:\-\s]*$|^[fF:\-\s]*$")
_MAC_LIKE_KEY = re.compile(r"(mac|bd_?addr|embedded_address|device_address)", re.I)
_WORD = re.compile(r"[A-Za-z_]+")
_OCTET = re.compile(r"[0-9A-Fa-f]{2}")


def bits_of(text: str) -> float:
    """Entropy estimate: per alphanumeric token, digits 3.32 bits/char, hex
    4 bits/char, anything else 5.17 bits/char."""
    total = 0.0
    for tok in _ALNUM.findall(text):
        if tok.isdigit():
            total += len(tok) * 3.32
        elif _HEX.fullmatch(tok):
            total += len(tok) * 4
        else:
            total += len(tok) * 5.17
    return round(total, 1)


def is_junk(value: str) -> bool:
    """No alphanumerics, all 0, all F, or one repeated character."""
    core = re.sub(r"[^0-9A-Za-z]", "", value)
    return not core or bool(_JUNK.match(value)) or len(set(core.lower())) <= 1


def stable_remainder(raw: str) -> str:
    """Strip leading word-only segments ("sonos:", "whoop_mode:", "mac:").

    A two-hex-digit segment is a MAC octet, not a word, so "mac:AA:BB:..."
    keeps its octets.
    """
    parts = raw.split(":")
    while len(parts) > 1 and _WORD.fullmatch(parts[0]) and not _OCTET.fullmatch(parts[0]):
        parts = parts[1:]
    return ":".join(parts)


def is_bad_mac(value: str) -> bool:
    """A 12-hex value with 4+ zero octets, or multicast in either byte order
    (the multicast bit set in both the first and the last octet)."""
    hexs = re.sub(r"[^0-9A-Fa-f]", "", value)
    if len(hexs) != 12:
        return False
    octets = [int(hexs[i:i + 2], 16) for i in range(0, 12, 2)]
    if sum(1 for o in octets if o == 0) >= 4:
        return True
    return bool(octets[0] & 1) and bool(octets[-1] & 1)


def classify_address(atype: str, addr: str) -> str:
    """public, random_static, resolvable_private, non_resolvable_private or
    reserved (adwatch's classify_mac_type)."""
    if (atype or "").lower() == "public":
        return "public"
    top = (int(addr.split(":")[0], 16) >> 6) & 0b11
    return {0b11: "random_static", 0b01: "resolvable_private", 0b00: "non_resolvable_private"}.get(top, "reserved")


def _hint(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z]", "", text)[-4:].upper()


@dataclass(frozen=True)
class Row:
    parser: str
    id_type: str
    confidence: str
    vendor: str | None
    product: str | None
    mobility: str
    key: str = ""        # meta key, or "stableKey"
    prefix: str = ""     # name families only

    @classmethod
    def from_dict(cls, d: dict) -> "Row":
        return cls(parser=d["parser"], id_type=d.get("id_type") or "", confidence=d.get("confidence") or "low",
                   vendor=d.get("vendor"), product=d.get("product"), mobility=d.get("mobility") or "unknown",
                   key=d.get("key", ""), prefix=d.get("prefix", ""))


@dataclass(frozen=True)
class IdentityKey:
    key: str            # e.g. "id:sonos:device_id:..." — raw; never written to disk
    kind: str           # id | sk | name | mac
    parser: str
    bits: float
    weak: bool
    hint: str           # last 4 characters of the identifying value
    id_type: str
    confidence: str
    vendor: str | None
    product: str | None
    mobility: str

    @property
    def payload(self) -> bool:
        return self.kind != "mac"


class FieldTable:
    """data/persistent_fields.json, indexed for lookups."""

    def __init__(self, raw: dict):
        rules = raw.get("rules", {})
        self.weak_bits = float(rules.get("weak_bits", 24))
        self.shared_threshold = int(rules.get("shared_if_concurrent_addresses", 3))
        self.token_re = re.compile(rules.get("name_token_regex", r"[0-9A-Fa-f]{4,}|\d{3,}"))
        self.skip_sk_prefixes = tuple(rules.get("skip_stable_key_prefixes", ["eddystone_eid:"]))
        self.unreliable = set(raw.get("unreliable_parsers", []))
        self.meta: dict[tuple[str, str], Row] = {}
        self.stable: dict[str, Row] = {}
        self.families: dict[str, list[Row]] = defaultdict(list)
        self.by_parser: dict[str, list[Row]] = defaultdict(list)
        for d in raw.get("fields", []):
            r = Row.from_dict(d)
            if d.get("source") == "stableKey":
                self.stable[r.parser] = r
            else:
                self.meta[(r.parser, r.key)] = r
            self.by_parser[r.parser].append(r)
        for d in raw.get("name_families", []):
            r = Row.from_dict(d)
            self.families[r.parser].append(r)
            self.by_parser[r.parser].append(r)
        for rows in self.families.values():
            rows.sort(key=lambda r: -len(r.prefix))  # longest prefix wins

    @classmethod
    def from_dict(cls, raw: dict) -> "FieldTable":
        return cls(raw)

    @classmethod
    def load(cls, path: str | Path) -> "FieldTable":
        return cls(json.loads(Path(path).read_text()))

    def parser_mobility(self, parsers) -> str:
        """Majority mobility of the table rows for these parsers, ignoring
        unknown; "unknown" when there are none (MAC-only units, SPEC §4.4)."""
        counts: dict[str, int] = defaultdict(int)
        for p in parsers:
            for r in self.by_parser.get(p, ()):
                if r.mobility != "unknown":
                    counts[r.mobility] += 1
        if not counts:
            return "unknown"
        return max(sorted(counts), key=lambda m: counts[m])

    def parser_row(self, parsers) -> Row | None:
        """The best-confidence row for any of these parsers (vendor and product
        for MAC-only units)."""
        rows = [r for p in parsers for r in self.by_parser.get(p, ())]
        return min(rows, key=lambda r: CONFIDENCE_RANK.get(r.confidence, 3)) if rows else None


class Resolver:
    def __init__(self, table: FieldTable, include_low_confidence: bool = False):
        self.table = table
        self.include_low = include_low_confidence

    def _usable(self, row: Row | None) -> bool:
        if row is None or row.parser in self.table.unreliable:
            return False
        return row.confidence in ("high", "medium") or (self.include_low and row.confidence == "low")

    def _key(self, kind: str, parser: str, text: str, bits: float, hint: str, row: Row) -> IdentityKey:
        return IdentityKey(key=text, kind=kind, parser=parser, bits=bits, weak=bits < self.table.weak_bits,
                           hint=hint, id_type=row.id_type, confidence=row.confidence, vendor=row.vendor,
                           product=row.product, mobility=row.mobility)

    def resolve(self, ad: dict, results: list[dict]) -> list[IdentityKey]:
        out: dict[str, IdentityKey] = {}

        def add(k: IdentityKey) -> None:
            out.setdefault(k.key, k)

        parsers = []
        for res in results:
            parser = res.get("parser") or ""
            parsers.append(parser)
            if parser in self.table.unreliable:
                continue
            for key, value in (res.get("metadata") or {}).items():
                row = self.table.meta.get((parser, key))
                if not self._usable(row) or value is None:
                    continue
                value = str(value)
                if len(value) < 2 or is_junk(value):
                    continue
                if _MAC_LIKE_KEY.search(key) and is_bad_mac(value):
                    continue
                add(self._key("id", parser, f"id:{parser}:{key}:{value}", bits_of(value), _hint(value), row))
            sk = res.get("stableKey")
            row = self.table.stable.get(parser)
            if sk and self._usable(row) and not sk.startswith(self.table.skip_sk_prefixes):
                rem = stable_remainder(sk)
                if not is_junk(rem):
                    add(self._key("sk", parser, f"sk:{parser}:{sk}", bits_of(rem), _hint(rem), row))

        name = ad.get("name")
        if name:
            for parser in (parsers or ["unparsed"]):
                k = self._name_key(parser, name)
                if k:
                    add(k)

        if classify_address(ad.get("atype") or "random", ad["addr"]) in ("public", "random_static"):
            addr = ad["addr"].upper()
            add(IdentityKey(key=f"mac:{addr}", kind="mac", parser="", bits=MAC_BITS, weak=False,
                            hint=_hint(addr), id_type="Stable MAC address", confidence="high",
                            vendor=None, product=None, mobility="unknown"))
        return list(out.values())

    def _name_key(self, parser: str, name: str) -> IdentityKey | None:
        if parser in self.table.unreliable:
            return None
        for row in self.table.families.get(parser, ()):
            if not self._usable(row) or not name.startswith(row.prefix):
                continue
            tokens = self.table.token_re.findall(name[len(row.prefix):])
            joined = " ".join(tokens)
            if not tokens or is_junk(joined):
                continue
            return self._key("name", parser, f"name:{parser}:{name}", bits_of(joined), _hint(tokens[-1]), row)
        return None


class SharedGuard:
    """A payload value seen from N or more distinct addresses within a window
    is a fleet or default value, not a unit (SPEC §4.3 step 4). Once shared,
    always shared; the caller persists the verdict."""

    def __init__(self, threshold: int = 3, window_s: float = 60.0, shared: set | None = None):
        self.threshold = threshold
        self.window = window_s
        self.shared: set = set(shared or ())
        self._seen: dict[str, dict[str, float]] = {}

    def is_shared(self, key: str) -> bool:
        return key in self.shared

    def observe(self, key: str, addr: str, t: float) -> bool:
        """Record a sighting; True when the key is (now) shared."""
        if key in self.shared:
            return True
        seen = self._seen.setdefault(key, {})
        seen[addr] = t
        for a in [a for a, at in seen.items() if t - at > self.window]:
            del seen[a]
        if len(seen) >= self.threshold:
            self.shared.add(key)
            del self._seen[key]
            return True
        return False

    def prune(self, now: float) -> None:
        for key in list(self._seen):
            seen = self._seen[key]
            if all(now - at > self.window for at in seen.values()):
                del self._seen[key]

    def tracked(self) -> int:
        return len(self._seen)
