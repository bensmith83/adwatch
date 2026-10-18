import re
from pathlib import Path

from porchlight.config import Config, load

REPO = Path(__file__).resolve().parent.parent


def test_the_example_config_loads_and_matches_the_defaults():
    c = load(REPO / "deploy" / "config.example.toml")
    d = Config()
    assert c.presence == d.presence and c.rules == d.rules and c.identity == d.identity
    assert c.learning == d.learning and c.web == d.web and c.debug == d.debug
    assert c.arming.mode == d.arming.mode and c.arming.away_after_minutes == d.arming.away_after_minutes
    assert c.arming.schedule == [{"days": "mon-fri", "from": "08:30", "to": "17:30"}]
    assert (c.adapter, c.db, c.fields, c.parser_bin) == (d.adapter, d.db, d.fields, d.parser_bin)


def test_the_service_runs_what_install_puts_in_place():
    unit = (REPO / "deploy" / "porchlight.service").read_text()
    install = (REPO / "deploy" / "install.sh").read_text()
    exec_start = re.search(r"^ExecStart=(\S+)", unit, re.M).group(1)
    assert exec_start == "/opt/porchlight/venv/bin/porchlight"
    assert "opt=/opt/porchlight" in install and "$opt/venv" in install and "porchlight.service" in install
    assert "User=porchlight" in unit
    assert '"$opt/bin/ble-parse"' in install and '"$opt/bin/ble-parse" --info' in install


def test_gitignore_covers_runtime_state():
    gi = (REPO / ".gitignore").read_text().split()
    for pattern in ("*.db", "secret", "bin/", "data/", "capture*.jsonl"):
        assert pattern in gi
