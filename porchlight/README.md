# Porchlight

A Raspberry Pi that listens to Bluetooth Low Energy advertisements around a house, learns what normally
appears there, and raises alerts when:

1. **A stranger lingers:** an unknown device stays near for a while (R1).
2. **A visitor keeps coming back:** an unknown device returns on several different days (R2).
3. **Something is new while armed:** any never-before-seen device appears while you're away (R3).
4. **A known device shows up at odd hours:** a device you know arrives outside its usual hours (R4).

It recognises devices by identifiers that survive address rotation (serial numbers, IMEIs, Tesla VIN hashes,
vendor device IDs, embedded MACs) or by a stable MAC address. See [SPEC.md](SPEC.md) for the full design.

Porchlight is its own app inside the adwatch repo: it shares no code with adwatch and installs on its own.

## What's here and what isn't

This folder is the whole app: the scanner, identity resolver, rules, storage, web page, notifiers, deploy
files and tests. Two pieces are **supplied separately** and are not in this repo:

- **`ble-parse`**, the parser binary. Porchlight runs it as a child process and talks to it over JSONL
  ([SPEC.md §4.1](SPEC.md#41-ble-parse-the-parser-contract)). `porchlight selftest` checks a binary against the
  contract.
- **`persistent_fields.json`**, the fields table that says which parser fields are per-device identifiers
  ([SPEC.md §10](SPEC.md#10-the-fields-table-persistent_fieldsjson)). It comes with the parser, because its
  names must match the parser's output.

Keep them in `bin/` and `data/` inside this folder; both are git-ignored.

## Build and test just this app

Needs Python 3.11 or later. Nothing from the rest of adwatch is installed or imported.

```sh
git clone https://github.com/bensmith83/adwatch
cd adwatch/porchlight

# with uv
uv sync && uv run pytest

# or with pip
python3 -m venv .venv && . .venv/bin/activate
pip install -e . pytest pytest-asyncio
pytest
```

The tests use a synthetic fields table (`tests/fields.json`) and need no Bluetooth. The replay scenarios and
the contract test also need a parser binary for the machine you're on; without one they skip. Point them at a
binary, and optionally at the real table:

```sh
PORCHLIGHT_PARSER_BIN=bin/macos/ble-parse PORCHLIGHT_FIELDS=data/persistent_fields.json pytest
```

## What it can and can't see

It **can** see cars (Teslas, trailer trackers, remote starters, dashcams, OBD dongles), worn and carried
devices (watches, fitness bands, rings, earbuds, glucose monitors, body cams) and household devices
(speakers, locks, appliances, sensors).

It **can't see phones.** iOS and Android rotate their Bluetooth addresses and broadcast no persistent ID, so a
person carrying only a phone is invisible. AirTag-style trackers rotate too, and Porchlight doesn't look for
unwanted trackers. The page says so too.

## Hardware

- Raspberry Pi Zero 2 W or better (Pi 3, 4, 5) on **64-bit** Raspberry Pi OS Lite, Bookworm or later.
  The original Pi Zero W (armv6) is not supported: the parser is a 64-bit ARM binary.
- The onboard Bluetooth works. A USB BLE dongle with an external antenna gives more range, and spares the
  Zero 2 W's shared Wi-Fi/Bluetooth radio. Set `adapter` (default `hci0`).

## Install on a Pi

Put the supplied parser and table in place first, then copy this folder over and run the installer. Nothing
needs compiling on the Pi.

```sh
# In adwatch/porchlight, with:
#   bin/linux-aarch64/ble-parse     the static linux-aarch64 parser
#   data/persistent_fields.json     its fields table
rsync -a --exclude .venv ./ pi@porch.local:porchlight/

# On the Pi:
cd porchlight && sudo deploy/install.sh
```

`install.sh` creates a `porchlight` system user (in the `bluetooth` group), installs to `/opt/porchlight`
(a venv with bleak and aiohttp), writes `/etc/porchlight/config.toml` from
[deploy/config.example.toml](deploy/config.example.toml) if there isn't one, runs `porchlight selftest` (the
parser contract against the installed binary) and starts `porchlight.service`.

```sh
journalctl -u porchlight -f     # logs, including alerts from the log notifier
porchlight status               # units near now
```

**The page** binds to `127.0.0.1:8080`. Reach it with `ssh -L 8080:localhost:8080 pi@porch.local`, or open it to
the LAN with `web.listen = "0.0.0.0"` plus a `web.token`, then visit `http://porch.local:8080/?token=<token>`
once (it sets a cookie). LAN only: there is no TLS in v1.

## Using it

**Learning.** For the first `learning_days` (7) nothing is pushed; the page lists what *would* have alerted so
you can tune thresholds. When learning ends, the neighbours' fixed devices (anything fixed or movable that came
near) and the regulars (anything seen on 3+ days) are baselined as known. **Re-learn** on the page resets the
baseline and keeps your labels.

**Labels** are the main tuning knob, settable from the device list or straight from an alert:

| Label | Effect |
|---|---|
| `household` | Your own devices. Presence keys; never alert. |
| `known` | Neighbours and regular visitors. Only R4 (odd hours) applies. |
| `ignore` | Never alerts. |

**Arming** (`arming.mode`): `always`; `manual` (the page toggle or `POST /api/arm`, kept across restarts);
`schedule` (weekly windows, which may cross midnight); or `presence`, which arms when no `household` device has
been near for `away_after_minutes` and disarms as soon as one is. Phones can't be presence keys. Use a watch,
car, earbuds or fitness band. Only devices with a strong ID (24+ bits, or a stable MAC) count. In every mode an
override from the page lasts until the next automatic transition.

**Rules** (defaults in [deploy/config.example.toml](deploy/config.example.toml)):

| Rule | Fires when | Severity |
|---|---|---|
| R1 | An unknown device's near visit reaches `linger_minutes` (10). | `alert`; fixed/movable devices only get an `info` entry, never pushed |
| R2 | An unknown mobile device was near on `repeat_days` (3) distinct days within `repeat_window_days` (14). | `alert` |
| R3 | Armed, and a never-seen device has been near for `armed_min_dwell_seconds` (60). | `alert` |
| R4 | A `known` (or baselined mobile) device with 5+ visits on 3+ days arrives more than an hour from any usual arrival time, or inside `quiet_hours`. | `warn` |

A visit is *near* when its strongest sighting reaches `rssi_floor` (−80 dBm). A per-device cooldown
(`cooldown_minutes`, 30) applies across all rules. A device known only by short (< 24-bit) tokens can still
alert, but the alert says "weak ID, may be a different device".

**Notifiers** (`[[notify]]`, each with a `min_severity`): `log` (journald), `ntfy`, `webhook` and `mqtt`
(alerts plus a retained armed state, with optional Home Assistant discovery). The page is always on. A failing
notifier is retried a few times, then the alert is dropped and logged; it never holds up scanning.

## Privacy

- Identifiers are stored only as **HMAC-SHA256** under a local secret, `/var/lib/porchlight/secret` (mode
  0600, created on first run). Raw values never touch disk; a device keeps only a 4-character hint.
  **If the secret is lost, every device is new again**: labels and history can no longer be matched.
- The page, the API and notifications show only vendor, product, ID type and the hint ("…3F2A").
- `debug.capture_jsonl` is off by default. It is the only store of raw identifiers (for replay and tuning),
  rotates daily with a size cap, and keeps a week.
- Nothing is uploaded anywhere. It never connects to a device: receive only, no GATT.

## Tuning with replay

```sh
porchlight replay capture-2026-10-17.jsonl --speed max     # or 1x; --json for machine-readable output
```

Replay runs a capture through the whole pipeline on a simulated clock, with no Bluetooth, against a throwaway
database. It works on the Pi, or on a Mac with a macOS build of the parser (`--parser-bin`).

## Development

```
porchlight/         Python: config, scanner, sidecar (the parser child), resolver, units, visits, rules,
                    arming, learning, store, engine, pipeline, replay, notify/, web/, cli
tests/              pytest (unit tests, replay scenarios); fields.json is the synthetic table
deploy/             porchlight.service, install.sh, config.example.toml
scripts/            bench_parser.py
bin/, data/         the supplied parser and table (git-ignored)
```

```sh
uv run pytest                                 # tests (scenarios skip without a parser binary)
porchlight selftest --parser-bin <binary>     # the parser contract
python3 scripts/bench_parser.py <binary>      # parser throughput and peak RSS against the budget
```

Everything is written red/green TDD. Fixtures use only obviously fake identifiers (`C0:FF:EE:…`, `TEST0001`),
and the real fields table never goes in the repo.

### Parser measurements (M0)

| Where | Throughput | Peak RSS |
|---|---|---|
| Budget (Pi Zero 2 W) | ≥ 200 ads/s | < 60 MB |
| Mac (M-series), native build | 6,300 ads/s | 13 MB |
| Static linux-aarch64 binary, arm64 Debian 12 container on the Mac | 6,200 ads/s | 22 MB |
| Pi Zero 2 W | *to measure:* `python3 scripts/bench_parser.py /opt/porchlight/bin/ble-parse` | |

The live pipeline only sends changed payloads to the parser (a device sitting still repeats itself), and the
scanner passes at most one sighting per second per (address, payload).

### On-device acceptance

Run for 24 hours at home on a Zero 2 W, then check:

```sh
# ps's %cpu is the average over each process's lifetime; 4 cores = 400%, so "under 30%" means under 120 here
ps -o %cpu=,rss=,comm= -C porchlight,ble-parse | awk '{c+=$1; r+=$2} END {print c "% CPU, " r/1024 " MB RSS"}'
journalctl -u porchlight --since -24h | grep -cE 'ALERT|WARN R[1-4]'    # alerts pushed: no storms
```

Targets: average total CPU under 30% of the machine, total RSS under 150 MB, no alert storms.

Also confirm that a device sitting still keeps producing sightings at least every ~10 s
(`porchlight status` shows its visit growing). Porchlight turns off BlueZ duplicate filtering
(`DuplicateData`) for exactly this.
