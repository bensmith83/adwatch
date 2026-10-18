"""porchlight run | status | replay | selftest"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

from .config import DEFAULT_PATH, ConfigError, load
from .model import Unit
from .rules import describe


def _setup_logging(verbose: bool = False) -> None:
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s", stream=sys.stdout)


def cmd_run(args, cfg) -> int:
    from . import app
    _setup_logging(args.verbose)
    try:
        asyncio.run(app.App(cfg).run_forever())
    except Exception as e:
        logging.getLogger("porchlight").error("cannot run: %s", e, exc_info=args.verbose)
        return 1
    return 0


def _dur(s: float) -> str:
    s = max(0, int(s))
    return f"{s} s" if s < 60 else f"{s // 60} min" if s < 3600 else f"{s / 3600:.1f} h"


def cmd_status(args, cfg) -> int:
    path = Path(cfg.db)
    if not path.exists():
        print(f"no database at {path} yet: is porchlight running?")
        return 0
    try:
        db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        db.execute("SELECT 1 FROM units LIMIT 1")
    except sqlite3.Error:
        db = sqlite3.connect(path)
    now = time.time()
    gap = cfg.presence.visit_gap_minutes * 60
    state = {k: json.loads(v) for k, v in db.execute("SELECT k, v FROM state")}
    armed = state.get("armed_effective", state.get("armed"))
    print(f"mode: {cfg.arming.mode}   armed: {'yes' if armed else 'no' if armed is not None else '?'}")
    rows = db.execute(
        "SELECT u.id, u.vendor, u.product, u.id_types, u.mobility, u.weak, u.label, u.label_name, u.hint,"
        " v.start, v.end, v.max_rssi FROM visits v JOIN units u ON u.id = v.unit_id"
        " WHERE v.end >= ? ORDER BY v.max_rssi DESC", (now - gap - 60,)).fetchall()
    seen = set()
    near = []
    for r in rows:
        if r[0] in seen:
            continue
        seen.add(r[0])
        u = Unit(id=r[0], vendor=r[1], product=r[2], id_types=set(filter(None, (r[3] or "").split(","))),
                 mobility=r[4], weak=bool(r[5]), label=r[6], label_name=r[7] or "", hint=r[8] or "")
        near.append((u, r[9], r[10], r[11]))
    print(f"near now ({len(near)}; open visits are checkpointed every minute):")
    for u, start, end, max_rssi in near:
        flag = "near" if max_rssi >= cfg.presence.rssi_floor else "far "
        label = f" [{u.label}]" if u.label else ""
        print(f"  {flag} {max_rssi:4d} dBm  {_dur(end - start):>7}  {u.mobility:<10} {describe(u)}{label}")
    if not near:
        print("  nothing")
    return 0


def cmd_replay(args, cfg) -> int:
    from .engine import Engine
    from .replay import replay
    from .resolver import FieldTable
    from .sidecar import Sidecar
    from .store import Store

    _setup_logging(args.verbose)
    if not args.verbose:
        logging.getLogger().setLevel(logging.WARNING)
    db = Path(args.db) if args.db else Path(tempfile.mkdtemp(prefix="porchlight-replay-")) / "replay.db"
    tz = None
    if args.tz:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(args.tz)
    store = Store(db)
    first_t = None
    with open(args.capture) as f:
        for line in f:
            try:
                first_t = json.loads(line)["t"] / 1000.0
                break
            except (ValueError, KeyError, TypeError):
                continue
    engine = Engine(cfg, FieldTable.load(cfg.fields), store, now=first_t or time.time(), tz=tz)
    pushed = []
    engine.on_alert.append(lambda a, u, p: p and pushed.append(a.id))

    async def go():
        sc = Sidecar([args.parser_bin or cfg.parser_bin])
        await sc.start()
        try:
            return await replay(args.capture, engine, sc.parse, speed=args.speed)
        finally:
            await sc.stop()

    stats = asyncio.run(go())
    alerts = sorted(engine.alerts.alerts.values(), key=lambda a: a.created)
    summary = {
        "ads": stats.ads, "bad_lines": stats.bad_lines, "dropped": stats.dropped,
        "first": stats.first, "last": stats.last, "db": str(db),
        "alerts": [dict(engine.alert_view(a), pushed=a.id in pushed) for a in alerts],
        "units": [dict(engine.unit_view(u), visits=len(engine.visits.history.get(u.id, [])))
                  for u in sorted(engine.units.units.values(), key=lambda u: u.first_seen)],
    }
    store.close()
    if args.json:
        print(json.dumps(summary, indent=1))
        return 0
    span = (stats.last - stats.first) if stats.first is not None else 0
    print(f"{stats.ads} ads over {_dur(span)}; {stats.bad_lines} bad lines; {stats.dropped} dropped; db {db}")
    print(f"{len(summary['units'])} units, {len(alerts)} entries:")
    from .timeutil import fmt_local, local_zone
    for a in summary["alerts"]:
        tag = "would-have " if a["learning"] else ""
        print(f"  {fmt_local(a['created'], tz or local_zone())}  {tag}{a['severity']:<5} {a['rule']}  {a['message']}")
    return 0


def cmd_selftest(args, cfg) -> int:
    from .sidecar import binary_info, run_contract

    cmd = [args.parser_bin or cfg.parser_bin]

    async def go():
        info = await binary_info(cmd)
        if not info:
            print(f"cannot run {cmd[0]} --info")
            return 1
        print(f"parsers: {info.get('parsers')}  commit: {info.get('commit')}")
        failures = await run_contract(cmd)
        for f in failures:
            print("  FAIL", f)
        print("contract: ok" if not failures else f"contract: {len(failures)} failures")
        return 0 if not failures else 1

    return asyncio.run(go())


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="porchlight", description="A BLE home alarm")
    p.add_argument("--config", default=DEFAULT_PATH)
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", default=argparse.SUPPRESS)
    common.add_argument("-v", "--verbose", action="store_true", default=argparse.SUPPRESS)
    sub.add_parser("run", parents=[common], help="scan and alarm (what systemd runs)")
    sub.add_parser("status", parents=[common], help="units near now, from the database")
    r = sub.add_parser("replay", parents=[common], help="run a capture through the pipeline on a simulated clock")
    r.add_argument("capture")
    r.add_argument("--speed", choices=("max", "1x"), default="max")
    r.add_argument("--db", help="database to use (default: a fresh temporary one)")
    r.add_argument("--parser-bin")
    r.add_argument("--tz", help="time zone for days and hours (default: local)")
    r.add_argument("--json", action="store_true")
    s = sub.add_parser("selftest", parents=[common], help="run the sidecar contract against the parser binary")
    s.add_argument("--parser-bin")
    args = p.parse_args(argv)
    try:
        cfg = load(args.config)
    except ConfigError as e:
        print(f"config error: {e}", file=sys.stderr)
        return 2
    handler = {"run": cmd_run, "status": cmd_status, "replay": cmd_replay, "selftest": cmd_selftest}
    return handler[args.cmd or "run"](args, cfg)


if __name__ == "__main__":
    sys.exit(main())
