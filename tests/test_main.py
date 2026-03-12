"""Tests for adwatch CLI entry point."""

import argparse
from unittest.mock import patch, AsyncMock, MagicMock

import pytest


def test_parse_args_defaults():
    from adwatch.main import parse_args

    args = parse_args([])
    assert args.no_dashboard is False
    assert args.list_plugins is False
    assert args.disable is None


def test_parse_args_no_dashboard():
    from adwatch.main import parse_args

    args = parse_args(["--no-dashboard"])
    assert args.no_dashboard is True


def test_parse_args_adapter():
    from adwatch.main import parse_args

    args = parse_args(["--adapter", "hci1"])
    assert args.adapter == "hci1"


def test_parse_args_db():
    from adwatch.main import parse_args

    args = parse_args(["--db", "/tmp/test.db"])
    assert args.db == "/tmp/test.db"


def test_parse_args_port():
    from adwatch.main import parse_args

    args = parse_args(["--port", "9090"])
    assert args.port == 9090


def test_parse_args_default_host_is_localhost():
    from adwatch.main import parse_args

    args = parse_args([])
    assert args.host == "127.0.0.1"


def test_parse_args_list_plugins():
    from adwatch.main import parse_args

    args = parse_args(["--list-plugins"])
    assert args.list_plugins is True


def test_parse_args_disable():
    from adwatch.main import parse_args

    args = parse_args(["--disable", "thermopro,matter"])
    assert args.disable == "thermopro,matter"


def test_cli_entry_point_exists():
    from adwatch.main import cli

    assert callable(cli)


def test_list_plugins_exits_cleanly(capsys):
    """--list-plugins should print plugin info and exit."""
    from adwatch.main import list_plugins
    from adwatch.registry import ParserRegistry

    reg = ParserRegistry()
    reg.register(
        name="test_parser",
        company_id=0x1234,
        description="Test parser",
        version="1.0.0",
        core=True,
        instance=MagicMock(),
    )
    list_plugins(reg)
    captured = capsys.readouterr()
    assert "test_parser" in captured.out
    assert "1.0.0" in captured.out


@pytest.mark.asyncio
async def test_shutdown_sets_server_should_exit():
    """Signal handler should set server.should_exit so uvicorn stops promptly."""
    from adwatch.main import _make_signal_handler

    scanner = MagicMock()
    scanner.stop = AsyncMock()

    class FakeServer:
        should_exit = False

    server = FakeServer()
    handler = _make_signal_handler(server, scanner)
    handler()

    assert server.should_exit is True


@pytest.mark.asyncio
async def test_shutdown_stops_scanner():
    """Signal handler should schedule scanner.stop()."""
    import asyncio
    from adwatch.main import _make_signal_handler

    scanner = MagicMock()
    scanner.stop = AsyncMock()

    class FakeServer:
        should_exit = False

    server = FakeServer()
    handler = _make_signal_handler(server, scanner)
    handler()

    # Let scheduled tasks run
    await asyncio.sleep(0.05)
    scanner.stop.assert_awaited_once()


def test_force_quit_on_second_signal():
    """Second signal should call sys.exit for force quit."""
    from adwatch.main import _make_signal_handler

    scanner = MagicMock()
    scanner.stop = AsyncMock()

    class FakeServer:
        should_exit = False

    server = FakeServer()
    handler = _make_signal_handler(server, scanner)

    # First call sets should_exit
    handler()
    assert server.should_exit is True

    # Second call should force exit
    with pytest.raises(SystemExit):
        handler()
