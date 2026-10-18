"""The parser child process, ble-parse (SPEC §4.1).

One long-lived child; one JSON line out, one JSON line back, in order. If the
child dies it is restarted with backoff while scanning carries on: ads that
arrive during the gap are dropped (parse() returns None) and the drop is
logged.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import OrderedDict, deque
from pathlib import Path

log = logging.getLogger(__name__)

CONTRACT = Path(__file__).with_name("sidecar_contract.json")
_CONTENT_FIELDS = ("addr", "atype", "mfr", "svc", "uuids", "name")


def ad_line(ad: dict) -> bytes:
    return (json.dumps(ad, separators=(",", ":")) + "\n").encode()


class Sidecar:
    def __init__(self, cmd: list[str], backoff_initial: float = 1.0, backoff_max: float = 30.0):
        self.cmd = cmd
        self.backoff_initial = backoff_initial
        self.backoff_max = backoff_max
        self.dropped = 0
        self.restarts = 0
        self._proc: asyncio.subprocess.Process | None = None
        self._pending: deque[asyncio.Future] = deque()
        self._ready = asyncio.Event()
        self._attempted = asyncio.Event()   # the first spawn has been tried
        self._task: asyncio.Task | None = None
        self._stopping = False
        self._gap_drops = 0

    async def start(self) -> None:
        self._task = asyncio.create_task(self._supervise())
        await self._attempted.wait()

    async def stop(self) -> None:
        self._stopping = True
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
        await self._kill()
        self._fail_pending()

    async def parse(self, ad: dict) -> list[dict] | None:
        """The parser results for one ad, or None if it had to be dropped."""
        proc = self._proc
        if not self._ready.is_set() or proc is None or proc.stdin is None:
            self.dropped += 1
            self._gap_drops += 1
            return None
        fut = asyncio.get_running_loop().create_future()
        self._pending.append(fut)
        try:
            proc.stdin.write(ad_line(ad))
            await proc.stdin.drain()
        except (BrokenPipeError, ConnectionResetError):
            pass  # the reader sees EOF and fails the future
        return await fut

    async def _supervise(self) -> None:
        backoff = self.backoff_initial
        loop = asyncio.get_running_loop()
        while not self._stopping:
            started = loop.time()
            try:
                self._proc = await asyncio.create_subprocess_exec(
                    *self.cmd, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                    limit=1 << 20)
            except OSError as e:
                log.error("cannot start ble-parse (%s): %s", self.cmd[0], e)
                self._attempted.set()
            else:
                if self._gap_drops:
                    log.warning("ble-parse restarted; dropped %d ads while it was down", self._gap_drops)
                    self._gap_drops = 0
                self._ready.set()
                self._attempted.set()
                await self._read(self._proc)
                self._ready.clear()
                code = await self._proc.wait()
                lost = len(self._pending)
                self._fail_pending()
                if self._stopping:
                    return
                log.warning("ble-parse exited with %s; dropped %d in-flight ads; restarting in %.1fs",
                            code, lost, backoff)
            if loop.time() - started > 60:
                backoff = self.backoff_initial
            await asyncio.sleep(backoff)
            self.restarts += 1
            backoff = min(backoff * 2, self.backoff_max)

    async def _read(self, proc) -> None:
        while True:
            line = await proc.stdout.readline()
            if not line:
                return
            if not self._pending:
                log.error("ble-parse answered with no question pending")
                continue
            fut = self._pending.popleft()
            try:
                doc = json.loads(line)
                results = doc.get("results", [])
                if doc.get("error"):
                    log.debug("ble-parse: %s", doc["error"])
            except (ValueError, AttributeError):
                results = []
            if not fut.done():
                fut.set_result(results)

    def _fail_pending(self) -> None:
        while self._pending:
            fut = self._pending.popleft()
            self.dropped += 1
            if not fut.done():
                fut.set_result(None)

    async def _kill(self) -> None:
        proc = self._proc
        if proc is None or proc.returncode is not None:
            return
        try:
            if proc.stdin:
                proc.stdin.close()
            await asyncio.wait_for(proc.wait(), timeout=2)
        except (asyncio.TimeoutError, ProcessLookupError):
            proc.kill()
            await proc.wait()


async def binary_info(cmd: list[str]) -> dict:
    """`ble-parse --info` as a dict (parsers, commit)."""
    try:
        proc = await asyncio.create_subprocess_exec(*cmd, "--info", stdout=asyncio.subprocess.PIPE)
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
    except (OSError, asyncio.TimeoutError):
        return {}
    info = {}
    for line in out.decode(errors="replace").splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            info[k.strip()] = v.strip()
    return info


class ParseCache:
    """Parse results by ad content. A device sitting still repeats the same
    payload, so only changed payloads need the parser. RSSI, time and TX
    power are not part of the key."""

    def __init__(self, maxsize: int = 4096):
        self.maxsize = maxsize
        self._d: OrderedDict[str, list] = OrderedDict()

    @staticmethod
    def key(ad: dict) -> str:
        return json.dumps([ad.get(f) for f in _CONTENT_FIELDS], sort_keys=True, separators=(",", ":"))

    def get(self, ad: dict):
        k = self.key(ad)
        hit = self._d.get(k)
        if hit is not None:
            self._d.move_to_end(k)
        return hit

    def put(self, ad: dict, results: list) -> None:
        k = self.key(ad)
        self._d[k] = results
        self._d.move_to_end(k)
        while len(self._d) > self.maxsize:
            self._d.popitem(last=False)

    def __len__(self) -> int:
        return len(self._d)


async def run_contract(cmd: list[str], contract: Path = CONTRACT) -> list[str]:
    """Run the contract fixture through a binary; a list of failures."""
    cases = json.loads(contract.read_text())["cases"]
    sc = Sidecar(cmd, backoff_initial=0.1)
    await sc.start()
    failures = []
    try:
        for case in cases:
            results = await sc.parse(case["ad"])
            if results is None:
                failures.append(f"{case['name']}: no answer")
                continue
            by_parser = {r["parser"]: r for r in results}
            if case.get("no_results") and results:
                failures.append(f"{case['name']}: expected no results, got {sorted(by_parser)}")
            for e in case["expect"]:
                r = by_parser.get(e["parser"])
                if r is None:
                    failures.append(f"{case['name']}: no {e['parser']} result (got {sorted(by_parser)})")
                    continue
                for k, v in (e.get("metadata") or {}).items():
                    if r["metadata"].get(k) != v:
                        failures.append(f"{case['name']}: {e['parser']}.{k} = {r['metadata'].get(k)!r}, want {v!r}")
                sk = e.get("stableKey")
                if sk is True and not r.get("stableKey"):
                    failures.append(f"{case['name']}: {e['parser']} has no stableKey")
                elif isinstance(sk, str) and r.get("stableKey") != sk:
                    failures.append(f"{case['name']}: {e['parser']}.stableKey = {r.get('stableKey')!r}, want {sk!r}")
    finally:
        await sc.stop()
    return failures
