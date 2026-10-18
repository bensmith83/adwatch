"""Configuration: one TOML file, every key optional (SPEC §5)."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any, get_type_hints

DEFAULT_PATH = "/etc/porchlight/config.toml"
SEVERITIES = ("info", "warn", "alert")
MODES = ("always", "manual", "schedule", "presence")
LOCALHOST = ("127.0.0.1", "localhost", "::1")


class ConfigError(ValueError):
    pass


@dataclass
class Identity:
    include_low_confidence: bool = False


@dataclass
class Presence:
    rssi_floor: int = -80
    visit_gap_minutes: float = 5


@dataclass
class Rules:
    linger_minutes: float = 10
    repeat_days: int = 3
    repeat_window_days: int = 14
    armed_min_dwell_seconds: float = 60
    cooldown_minutes: float = 30
    quiet_hours: str = ""


@dataclass
class Learning:
    learning_days: float = 7


@dataclass
class Arming:
    mode: str = "manual"
    away_after_minutes: float = 15
    schedule: list = field(default_factory=list)


@dataclass
class Web:
    listen: str = "127.0.0.1"
    port: int = 8080
    token: str = ""


@dataclass
class Notify:
    type: str = "log"
    min_severity: str = "warn"
    # Everything else in the [[notify]] table (url, token, host, ...), for the
    # notifier itself to read.
    options: dict = field(default_factory=dict)


@dataclass
class Debug:
    capture_jsonl: str = ""
    capture_max_mb: float = 50


@dataclass
class Config:
    adapter: str = "hci0"
    db: str = "/var/lib/porchlight/porchlight.db"
    fields: str = "/opt/porchlight/data/persistent_fields.json"
    parser_bin: str = "/opt/porchlight/bin/ble-parse"
    identity: Identity = field(default_factory=Identity)
    presence: Presence = field(default_factory=Presence)
    rules: Rules = field(default_factory=Rules)
    learning: Learning = field(default_factory=Learning)
    arming: Arming = field(default_factory=Arming)
    web: Web = field(default_factory=Web)
    notify: list = field(default_factory=lambda: [Notify()])
    debug: Debug = field(default_factory=Debug)


def load(path: str | Path = DEFAULT_PATH) -> Config:
    path = Path(path)
    if not path.exists():
        return Config()
    try:
        raw = tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{path}: {e}") from e
    return from_dict(raw)


def from_dict(raw: dict) -> Config:
    raw = dict(raw)
    notify_raw = raw.pop("notify", None)
    config = _build(Config, raw, "")
    if notify_raw is not None:
        if not isinstance(notify_raw, list):
            raise ConfigError("notify must be a list of [[notify]] tables")
        config.notify = [_notify(n, i) for i, n in enumerate(notify_raw)]
    _validate(config)
    return config


def _build(cls, raw: dict, prefix: str):
    hints = get_type_hints(cls)
    known = {f.name for f in fields(cls)}
    for key in raw:
        if key not in known:
            raise ConfigError(f"unknown config key {prefix}{key}")
    kwargs = {}
    for f in fields(cls):
        if f.name not in raw:
            continue
        value, kind = raw[f.name], hints[f.name]
        if is_dataclass(kind):
            if not isinstance(value, dict):
                raise ConfigError(f"[{prefix}{f.name}] must be a table")
            value = _build(kind, value, f"{prefix}{f.name}.")
        else:
            value = _check_type(value, kind, f"{prefix}{f.name}")
        kwargs[f.name] = value
    return cls(**kwargs)


def _check_type(value: Any, kind: Any, name: str):
    if kind is bool:
        ok = isinstance(value, bool)
    elif kind is int:
        ok = isinstance(value, int) and not isinstance(value, bool)
    elif kind is float:
        ok = isinstance(value, (int, float)) and not isinstance(value, bool)
        value = float(value) if ok else value
    elif kind is str:
        ok = isinstance(value, str)
    elif kind is list:
        ok = isinstance(value, list)
    elif kind is dict:
        ok = isinstance(value, dict)
    else:
        ok = True
    if not ok:
        raise ConfigError(f"{name} must be {getattr(kind, '__name__', kind)}, got {value!r}")
    return value


def _notify(raw: Any, index: int) -> Notify:
    if not isinstance(raw, dict):
        raise ConfigError(f"notify[{index}] must be a table")
    raw = dict(raw)
    n = Notify(
        type=_check_type(raw.pop("type", "log"), str, f"notify[{index}].type"),
        min_severity=_check_type(raw.pop("min_severity", "warn"), str, f"notify[{index}].min_severity"),
    )
    n.options = raw
    return n


def _validate(c: Config) -> None:
    if c.arming.mode not in MODES:
        raise ConfigError(f"arming.mode must be one of {', '.join(MODES)}, got {c.arming.mode!r}")
    if c.web.listen not in LOCALHOST and not c.web.token:
        raise ConfigError("web.listen beyond localhost requires web.token")
    for i, n in enumerate(c.notify):
        if n.min_severity not in SEVERITIES:
            raise ConfigError(f"notify[{i}].min_severity must be one of {', '.join(SEVERITIES)}")
