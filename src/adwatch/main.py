"""CLI entry point for adwatch BLE advertisement analyzer."""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys

from adwatch import config


logger = logging.getLogger("adwatch")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="adwatch",
        description="BLE advertisement analyzer with real-time dashboard",
    )
    parser.add_argument(
        "--no-dashboard", action="store_true",
        help="Scanner only, log to stdout",
    )
    parser.add_argument(
        "--adapter", default=config.ADAPTER,
        help=f"BLE adapter (default: {config.ADAPTER})",
    )
    parser.add_argument(
        "--db", default=config.DB_PATH,
        help=f"SQLite database path (default: {config.DB_PATH})",
    )
    parser.add_argument(
        "--port", type=int, default=config.PORT,
        help=f"Dashboard port (default: {config.PORT})",
    )
    parser.add_argument(
        "--list-plugins", action="store_true",
        help="Show loaded plugins and exit",
    )
    parser.add_argument(
        "--disable",
        help="Comma-separated plugin names to disable",
    )
    parser.add_argument(
        "--listen-network", action="store_true",
        help="Listen on all interfaces (0.0.0.0) instead of localhost",
    )
    args = parser.parse_args(argv)
    args.host = "0.0.0.0" if args.listen_network else config.HOST
    return args


def list_plugins(registry) -> None:
    parsers = registry.get_all()
    if not parsers:
        print("No plugins loaded.")
        return
    for p in parsers:
        kind = "core" if p.core else "plugin"
        print(f"  {p.name:24s} v{p.version:8s} [{kind}]  {p.description}")


def _make_signal_handler(server, scanner):
    """Create a signal handler that cleanly shuts down server and scanner.

    First call: sets server.should_exit and schedules scanner.stop().
    Second call: forces sys.exit(1).
    """
    called = False

    def handler():
        nonlocal called
        if called:
            logger.info("Force quit.")
            sys.exit(1)
        called = True
        logger.info("Shutting down...")
        server.should_exit = True
        asyncio.ensure_future(scanner.stop())

    return handler


async def _run(args: argparse.Namespace) -> None:
    from adwatch.storage.base import Database
    from adwatch.storage.migrations import run_migrations
    from adwatch.storage.raw import RawStorage
    from adwatch.classifier import Classifier
    from adwatch.registry import ParserRegistry
    from adwatch.dashboard.websocket import WebSocketManager, ThrottledEmitter
    from adwatch.pipeline import Pipeline
    from adwatch.scanner import Scanner

    # Determine disabled plugins
    disabled = set()
    if args.disable:
        disabled = {n.strip() for n in args.disable.split(",")}
    disabled |= set(config.DISABLED_PLUGINS)

    # Initialize components
    db = Database()
    await db.connect(args.db)

    raw_storage = RawStorage(db)
    classifier = Classifier()
    registry = ParserRegistry()

    # Import parser/plugin packages to trigger @register_parser decorators
    import adwatch.parsers  # noqa: F401
    import adwatch.plugins  # noqa: F401

    # Copy non-disabled entries from the default registry
    from adwatch.registry import _default_registry
    for entry in _default_registry._parsers:
        if entry["name"] not in disabled:
            registry.register(**{k: v for k, v in entry.items() if k != "enabled"})

    await run_migrations(db, registry=registry)

    if args.list_plugins:
        list_plugins(registry)
        await db.close()
        return

    ws_manager = WebSocketManager()
    throttled = ThrottledEmitter(ws_manager)
    pipeline = Pipeline(raw_storage, classifier, registry, throttled, db=db)
    scanner = Scanner(adapter=args.adapter)

    loop = asyncio.get_event_loop()

    if args.no_dashboard:
        stop_event = asyncio.Event()

        def _signal_handler():
            logger.info("Shutting down...")
            stop_event.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, _signal_handler)

        logger.info("Starting scanner (no dashboard)...")
        await throttled.start()
        await scanner.start(pipeline.process)
        await stop_event.wait()
    else:
        import uvicorn
        from adwatch.dashboard.app import create_app

        app = create_app(raw_storage, classifier, registry, ws_manager, db=db)
        uvi_config = uvicorn.Config(
            app, host=args.host, port=args.port, log_level=config.LOG_LEVEL.lower(),
        )
        server = uvicorn.Server(uvi_config)
        server.install_signal_handlers = lambda: None

        handler = _make_signal_handler(server, scanner)
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, handler)

        logger.info("Starting scanner + dashboard on %s:%d", args.host, args.port)
        await throttled.start()
        # Start scanner and server concurrently so the dashboard is available
        # even if the BLE adapter is slow or fails to start.
        scanner_task = asyncio.create_task(scanner.start(pipeline.process))
        try:
            await server.serve()
        finally:
            if not scanner_task.done():
                scanner_task.cancel()
            else:
                # Surface any scanner startup exception
                scanner_task.result()

    await scanner.stop()
    await throttled.stop()
    await db.close()
    logger.info("Shutdown complete.")


def cli() -> None:
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )
    try:
        asyncio.run(_run(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    cli()
