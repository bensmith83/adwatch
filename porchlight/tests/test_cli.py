import asyncio
import json
import time

import aiohttp
import pytest

import captures as C
from porchlight import cli
from porchlight.app import App
from porchlight.config import Config
from porchlight.model import KeyInfo, Unit, Visit
from porchlight.store import Store

from parser_paths import BIN, FIELDS, needs_bin


def write_config(tmp_path, extra=""):
    p = tmp_path / "config.toml"
    p.write_text(f"""
db = "{tmp_path / 'p.db'}"
fields = "{FIELDS}"
parser_bin = "{BIN}"
[learning]
learning_days = 0
{extra}
""")
    return p


@needs_bin
def test_replay_command_prints_a_json_summary(tmp_path, capsys):
    cap = C.write(tmp_path / "cap.jsonl", C.stay(C.tesla("0123456789abcdef"), 1_760_000_000, 15 * 60, 5, rssi=-65,
                                                  addr=C.rotating("5C:FF:EE:00")))
    code = cli.main(["replay", str(cap), "--config", str(write_config(tmp_path)), "--db", str(tmp_path / "r.db"),
                     "--json"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ads"] > 100
    assert [a["rule"] for a in out["alerts"]] == ["R1"]
    assert "0123456789abcdef" not in json.dumps(out)


def test_status_prints_units_near_now_masked(tmp_path, capsys):
    cfg = write_config(tmp_path)
    s = Store(tmp_path / "p.db")
    now = time.time()
    s.put_unit(Unit(id=1, vendor="Tesla", product="Vehicle", id_types={"Name-embedded VIN hash"}, mobility="vehicle",
                    weak=False, first_seen=now - 600, last_seen=now - 5, hint="DEFC"))
    s.put_unit(Unit(id=2, vendor="Sonos", product="Era 100", id_types={"Vendor device ID"}, mobility="fixed",
                    weak=False, first_seen=now - 9000, last_seen=now - 8000, hint="0001"))
    s.put_key(s.hmac("name:tesla:S0123456789abcdefC"), KeyInfo(1, "name", 68.0))
    s.put_visit(Visit(id=1, unit_id=1, start=now - 600, end=now - 5, n=60, max_rssi=-62, sum_rssi=-3900.0))
    s.put_visit(Visit(id=2, unit_id=2, start=now - 9000, end=now - 8000, n=60, max_rssi=-70, sum_rssi=-4200.0))
    s.set_state("armed", True)
    s.close()
    assert cli.main(["status", "--config", str(cfg)]) == 0
    out = capsys.readouterr().out
    assert "Vehicle" in out and "…DEFC" in out and "vehicle" in out
    assert "Era 100" not in out
    assert "S0123456789abcdefC" not in out


def test_status_with_no_database(tmp_path, capsys):
    assert cli.main(["status", "--config", str(write_config(tmp_path))]) == 0
    assert "no database" in capsys.readouterr().out.lower()


@needs_bin
def test_selftest_passes_with_the_real_parser(tmp_path, capsys):
    assert cli.main(["selftest", "--config", str(write_config(tmp_path))]) == 0
    out = capsys.readouterr().out
    assert "parsers:" in out and "contract: ok" in out


def test_selftest_fails_with_a_missing_parser(tmp_path, capsys):
    cfg = tmp_path / "c.toml"
    cfg.write_text(f'parser_bin = "{tmp_path / "nope"}"\nfields = "{FIELDS}"\n')
    assert cli.main(["selftest", "--config", str(cfg)]) == 1


def test_a_bad_config_exits_2(tmp_path, capsys):
    cfg = tmp_path / "c.toml"
    cfg.write_text("[presence]\nrssi_flor = 1\n")
    assert cli.main(["status", "--config", str(cfg)]) == 2
    assert "rssi_flor" in capsys.readouterr().err


class FakeScanner:
    def __init__(self, adapter, on_ad):
        self.on_ad = on_ad
        self.started = False

    async def start(self):
        self.started = True

    async def stop(self):
        self.started = False


@needs_bin
async def test_the_app_wires_scanner_parser_engine_and_page(tmp_path):
    cfg_path = write_config(tmp_path, '[web]\nport = 0\n')
    from porchlight.config import load
    cfg = load(cfg_path)
    app = App(cfg, scanner_factory=FakeScanner)
    await app.start()
    try:
        assert app.scanner.started
        now = time.time()
        for a in C.stay(C.whoop("4TEST0003"), now, 5, 1, rssi=-60, addr=C.fixed("5C:FF:EE:00:00:01")):
            app.scanner.on_ad(a)
        for _ in range(100):
            await asyncio.sleep(0.02)
            if app.engine.units.units:
                break
        async with aiohttp.ClientSession() as s:
            async with s.get(f"http://127.0.0.1:{app.port}/api/state") as r:
                state = await r.json()
        assert state["about"]["parsers"], "the About box shows the parser count"
        assert state["near"][0]["product"]
    finally:
        await app.stop()
    assert Store(tmp_path / "p.db").load().units, "flushed on stop"


class BrokenScanner(FakeScanner):
    async def start(self):
        raise RuntimeError("org.bluez not available")


@needs_bin
async def test_a_scanner_that_cannot_start_cleans_up_after_itself(tmp_path):
    from porchlight.config import load
    cfg = load(write_config(tmp_path, '[web]\nport = 0\n'))
    app = App(cfg, scanner_factory=BrokenScanner)
    with pytest.raises(RuntimeError, match="bluez"):
        await app.start()
    assert app.sidecar._proc.returncode is not None, "the parser child is stopped"
    assert app._runner is None or not app._runner.sites, "the page is closed"


def test_run_reports_a_failed_start_cleanly(tmp_path, caplog, monkeypatch):
    import porchlight.app as app_mod

    class Failing:
        def __init__(self, cfg):
            pass

        async def run_forever(self):
            raise RuntimeError("org.bluez not available")

    monkeypatch.setattr(app_mod, "App", Failing)
    assert cli.main(["run", "--config", str(write_config(tmp_path))]) == 1
    assert "cannot run: org.bluez not available" in caplog.text
