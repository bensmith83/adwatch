"""In-memory records shared by units, visits, rules and the store."""

from __future__ import annotations

from dataclasses import dataclass, field

LABELS = ("household", "known", "ignore")
SEVERITY_RANK = {"info": 0, "warn": 1, "alert": 2}
NO_MOBILITY_RANK = 9    # mobility not yet set by any table row


@dataclass(slots=True)
class Unit:
    """One physical device (SPEC §4.4)."""
    id: int
    vendor: str | None = None
    product: str | None = None
    id_types: set = field(default_factory=set)
    mobility: str = "unknown"
    weak: bool = True
    first_seen: float = 0.0
    last_seen: float = 0.0
    label: str | None = None
    label_name: str = ""
    hint: str = ""
    baseline: bool = False
    # Confidence rank of the table row the mobility came from (0 high .. 2
    # low, 3 parser majority, NO_MOBILITY_RANK none), so a better row wins.
    mobility_rank: int = NO_MOBILITY_RANK
    # Not persisted: the strength of the key the hint came from, so the hint
    # follows the strongest key. Rebuilt from unit_keys on load.
    hint_bits: float = 0.0

    @property
    def known(self) -> bool:
        return self.label is not None or self.baseline


@dataclass(slots=True)
class KeyInfo:
    unit_id: int | None
    kind: str
    bits: float
    shared: bool = False


@dataclass(slots=True)
class Visit:
    """An unbroken presence of one unit (SPEC §4.5)."""
    id: int
    unit_id: int
    start: float
    end: float
    n: int
    max_rssi: int
    sum_rssi: float
    last_rssi: int = 0      # not persisted: the latest sighting, for "near now"

    @property
    def avg_rssi(self) -> float:
        return self.sum_rssi / self.n if self.n else 0.0

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass(slots=True)
class Alert:
    id: int
    unit_id: int
    rule: str
    severity: str
    created: float
    acked: bool = False
    details: dict = field(default_factory=dict)
