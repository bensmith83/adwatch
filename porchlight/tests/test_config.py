import pytest

from porchlight.config import Config, ConfigError, load


def write(tmp_path, text):
    p = tmp_path / "config.toml"
    p.write_text(text)
    return p


def test_every_key_is_optional(tmp_path):
    c = load(write(tmp_path, ""))
    assert c.adapter == "hci0"
    assert c.db == "/var/lib/porchlight/porchlight.db"
    assert c.fields == "/opt/porchlight/data/persistent_fields.json"
    assert c.parser_bin == "/opt/porchlight/bin/ble-parse"
    assert c.identity.include_low_confidence is False
    assert c.presence.rssi_floor == -80
    assert c.presence.visit_gap_minutes == 5
    assert c.rules.linger_minutes == 10
    assert c.rules.repeat_days == 3
    assert c.rules.repeat_window_days == 14
    assert c.rules.armed_min_dwell_seconds == 60
    assert c.rules.cooldown_minutes == 30
    assert c.rules.quiet_hours == ""
    assert c.learning.learning_days == 7
    assert c.arming.mode == "manual"
    assert c.arming.away_after_minutes == 15
    assert c.arming.schedule == []
    assert c.web.listen == "127.0.0.1"
    assert c.web.port == 8080
    assert c.web.token == ""
    assert [(n.type, n.min_severity) for n in c.notify] == [("log", "warn")]
    assert c.debug.capture_jsonl == ""


def test_missing_file_means_defaults(tmp_path):
    assert load(tmp_path / "nope.toml") == Config()


def test_values_override_defaults(tmp_path):
    c = load(write(tmp_path, """
adapter = "hci1"
[presence]
rssi_floor = -75
[rules]
quiet_hours = "00:00-05:00"
[arming]
mode = "schedule"
schedule = [ { days = "mon-fri", from = "08:30", to = "17:30" } ]
[web]
listen = "0.0.0.0"
token = "s3cret"
[[notify]]
type = "ntfy"
min_severity = "alert"
url = "https://ntfy.example/topic"
"""))
    assert c.adapter == "hci1"
    assert c.presence.rssi_floor == -75
    assert c.rules.quiet_hours == "00:00-05:00"
    assert c.arming.mode == "schedule"
    assert c.arming.schedule == [{"days": "mon-fri", "from": "08:30", "to": "17:30"}]
    assert len(c.notify) == 1
    assert c.notify[0].type == "ntfy"
    assert c.notify[0].options == {"url": "https://ntfy.example/topic"}


def test_unknown_keys_are_rejected(tmp_path):
    with pytest.raises(ConfigError, match="rssi_flor"):
        load(write(tmp_path, "[presence]\nrssi_flor = -70\n"))


def test_bad_mode_is_rejected(tmp_path):
    with pytest.raises(ConfigError, match="mode"):
        load(write(tmp_path, '[arming]\nmode = "sometimes"\n'))


def test_listening_beyond_localhost_requires_a_token(tmp_path):
    with pytest.raises(ConfigError, match="token"):
        load(write(tmp_path, '[web]\nlisten = "0.0.0.0"\n'))


def test_bad_severity_is_rejected(tmp_path):
    with pytest.raises(ConfigError, match="min_severity"):
        load(write(tmp_path, '[[notify]]\ntype = "log"\nmin_severity = "loud"\n'))


def test_wrong_type_is_rejected(tmp_path):
    with pytest.raises(ConfigError, match="port"):
        load(write(tmp_path, '[web]\nport = "eighty"\n'))
