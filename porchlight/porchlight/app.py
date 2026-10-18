"""The live process: scanner -> sidecar -> engine -> notifiers, plus the page.
One asyncio loop; systemd runs it (deploy/porchlight.service)."""

from __future__ import annotations

import asyncio
import logging
import signal
import time

from aiohttp import web

from .capture import CaptureWriter
from .config import Config
from .engine import Engine
from .notify import Dispatcher, build_notifiers
from .pipeline import Pipeline
from .resolver import FieldTable
from .scanner import Scanner
from .sidecar import Sidecar, binary_info
from .store import Store
from .web.server import make_app

log = logging.getLogger(__name__)

STATUS_EVERY_S = 600


class App:
    def __init__(self, cfg: Config, scanner_factory=None, tz=None):
        self.cfg = cfg
        self.scanner_factory = scanner_factory or Scanner
        self.tz = tz
        self.port: int | None = None
        self._tasks: list[asyncio.Task] = []
        self._runner: web.AppRunner | None = None
        self.capture = None
        self.store = self.engine = self.sidecar = self.dispatcher = self.scanner = None

    async def start(self) -> None:
        """Start everything; if any part fails, stop what did start and re-raise."""
        try:
            await self._start()
        except BaseException:
            await self.stop()
            raise

    async def _start(self) -> None:
        cfg = self.cfg
        self.store = Store(cfg.db)
        self.engine = Engine(cfg, FieldTable.load(cfg.fields), self.store, now=time.time(), tz=self.tz)
        cmd = [cfg.parser_bin]
        self.engine.info = await binary_info(cmd)
        if not self.engine.info:
            log.error("%s --info failed: is the parser installed?", cfg.parser_bin)
        self.sidecar = Sidecar(cmd)
        await self.sidecar.start()

        self.dispatcher = Dispatcher(build_notifiers(cfg.notify))
        self.dispatcher.start()
        self.engine.on_alert.append(self._on_alert)
        self.engine.on_arming.append(self._on_arming)
        self.dispatcher.submit_armed(self.engine.arming.armed)
        self.store.set_state("armed_effective", self.engine.arming.armed)

        if cfg.debug.capture_jsonl:
            self.capture = CaptureWriter(cfg.debug.capture_jsonl, cfg.debug.capture_max_mb)
            log.warning("capturing raw advertisements to %s (debug only)", cfg.debug.capture_jsonl)
        self.pipeline = Pipeline(self.engine, self.sidecar.parse, capture=self.capture)
        self._tasks = [asyncio.create_task(self.pipeline.run()), asyncio.create_task(self._ticker())]

        self._runner = web.AppRunner(make_app(self.engine, cfg.web.token), access_log=None)
        await self._runner.setup()
        site = web.TCPSite(self._runner, cfg.web.listen, cfg.web.port)
        await site.start()
        self.port = self._runner.addresses[0][1] if self._runner.addresses else cfg.web.port
        log.info("page on http://%s:%s/", cfg.web.listen, self.port)

        scanner = self.scanner_factory(cfg.adapter, self.pipeline.offer)
        await scanner.start()
        self.scanner = scanner

    def _on_alert(self, alert, unit, pushed: bool) -> None:
        if pushed:
            self.dispatcher.submit(self.engine.alert_view(alert))

    def _on_arming(self, armed: bool) -> None:
        self.store.set_state("armed_effective", armed)
        self.dispatcher.submit_armed(armed)

    async def _ticker(self) -> None:
        last_status = time.time()
        while True:
            await asyncio.sleep(1)
            now = time.time()
            try:
                self.engine.tick(now)
            except Exception:
                log.exception("tick failed")
            if now - last_status >= STATUS_EVERY_S:
                last_status = now
                log.info("%.1f ads/s, %d units, %d near now, %d anonymous; dropped: %d queue, %d parser",
                         self.engine.ads_per_s, len(self.engine.units.units), len(self.engine.visits.open),
                         self.engine.anonymous_nearby(), self.pipeline.dropped, self.sidecar.dropped)

    async def stop(self) -> None:
        """Stop whatever is running; safe after a partial start."""
        if self.scanner:
            await self.scanner.stop()
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        if self._runner:
            await self._runner.cleanup()
            self._runner = None
        if self.dispatcher:
            await self.dispatcher.stop()
        if self.sidecar:
            await self.sidecar.stop()
        if self.engine:
            self.engine.shutdown()
        if self.store:
            self.store.close()
            self.store = None
        if self.capture:
            self.capture.close()

    async def run_forever(self) -> None:
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, stop.set)
        await self.start()
        try:
            await stop.wait()
        finally:
            log.info("stopping")
            await self.stop()
