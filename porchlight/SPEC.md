# Porchlight: a BLE home alarm

Spec v1.1, 2026-10-18. "Porchlight" is a working name, so rename it freely.

## 1. What it is

A Raspberry Pi that listens to Bluetooth Low Energy advertisements around a house. It recognises individual
devices by identifiers that survive MAC-address rotation (serial numbers, IMEIs, Tesla VIN hashes, vendor
device IDs, embedded MACs) or, when a device has one, by a stable MAC address. It learns what normally
appears there, and it raises alerts when:

1. **A stranger lingers.** An unknown device stays close for a while.
2. **A visitor keeps coming back.** An unknown device returns on several different days.
3. **Something is new while armed.** Any never-before-seen device appears while you're away.
4. **A known device shows up at odd hours.** A device you know arrives outside its usual hours.

Keep it small. It is one Python process and one stateless parser binary on one Pi, with a SQLite file and a
single web page. Don't build anything this spec doesn't ask for.

### What it can and can't see

It **can** see cars (Teslas, trailer IMEI trackers, remote-start modules, dashcams, OBD dongles), worn and
carried devices (smartwatches, fitness bands, rings, earbuds, bone-conduction headphones, glucose monitors,
body cams), and household devices (speakers, thermostats, locks, appliances, sensors).

It **can't** see phones. iOS and Android rotate their addresses and broadcast no persistent ID, so a person
carrying only a phone is invisible. AirTag-style trackers also rotate, and Porchlight doesn't look for
unwanted trackers. Make the page say so plainly.

## 2. What's in this repo and what isn't

Porchlight lives in the adwatch repo as its own app, in `porchlight/`. It shares no code with adwatch.

| Part | Where it comes from |
|---|---|
| **The app** (Python, this folder) | Built and tested from here. |
| **`ble-parse`**, the parser binary | Supplied separately, prebuilt. It must meet the contract in section 4.1, which `porchlight selftest` checks. |
| **The fields table** (`persistent_fields.json`) | Supplied with the parser, because its parser and key names must match the parser's output. Format in section 10. The tests use a small synthetic table, `tests/fields.json`. |
| **adwatch** (`../src/adwatch`) | Only as a reference: the bleak scanner callback (`scanner.py`, which reads `AddressType` from BlueZ props) and `classify_mac_type` (`models.py`). **Don't fork the rest of it.** Its plugins don't extract per-unit IDs (they were scrubbed by policy), and its dashboard is far bigger than we need. |

## 3. Hardware

- **Minimum: Pi Zero 2 W** (64-bit, 512 MB) running 64-bit Raspberry Pi OS Lite (Bookworm or later). A Pi 3, 4
  or 5 is fine.
- The **original Pi Zero W (armv6) is not supported**: the parser is a 64-bit ARM binary.
- The onboard Bluetooth works. A USB BLE dongle with an external antenna is optional: it gives more range, and
  the Zero 2 W's onboard chip shares one radio between Wi-Fi and Bluetooth. Make the adapter configurable
  (`hci0` by default).
- No compiler on the Pi. The parser arrives as one prebuilt binary.

## 4. Architecture

```
bleak scanner ──JSONL──▶ ble-parse ──JSONL──▶ resolver ─▶ units/visits ─▶ rules ─▶ notifiers
  (Python)               (child process,       (Python)                                  │
                          stateless)                └──────── SQLite ◀── web page ◀─────┘
```

- One asyncio Python process owns everything except parsing. It runs under systemd.
- Configuration is one TOML file (`tomllib`, standard library).
- Runtime dependencies are **bleak** and **aiohttp**, nothing else. Python 3.11 is what Bookworm ships.

### 4.1 `ble-parse` (the parser contract)

The parser is a separate binary so that it can be updated, and kept, apart from the app. The app talks to it
only through this contract.

**stdin.** One JSON object per line:

```json
{"t": 1760000000123, "addr": "C0:FF:EE:00:00:01", "atype": "random", "rssi": -67,
 "mfr": "4c000215...", "svc": {"0000fe07-0000-1000-8000-00805f9b34fb": "01ab"},
 "uuids": ["0000fe07-0000-1000-8000-00805f9b34fb"], "name": "S39 ABCD LE", "tx": null}
```

- `mfr` is the company ID (little-endian) followed by the payload, as hex, or null.
- UUIDs are sent as bleak reports them (lowercase, 128-bit). Normalising them is the parser's job.

**stdout.** One line per input line, in the same order, flushed after each line:

```json
{"results": [{"parser": "sonos", "beaconType": "sonos", "deviceClass": "speaker",
              "stableKey": "...", "metadata": {"device_id": "..."}}]}
```

- A line it can't read still gets an answer: empty `results` and an `error` string. It never exits on bad
  input, so lines always pair up.

**Other behaviour.**
- `ble-parse --info` prints `key: value` lines, including `parsers` (the parser count) and `commit` (what the
  binary was built from). The page's About box shows them.
- **Builds:** a static `linux-aarch64` binary for the Pi. A macOS build is handy for replay and the scenario
  tests on a Mac.
- **Budget:** at least 200 ads/s on a Zero 2 W, at under 60 MB RSS. `scripts/bench_parser.py` measures it.
- **Restarts:** the Python side runs it as a long-lived child. If the child dies, restart it with backoff and
  keep scanning. Ads that arrive during the gap are dropped, and the drop is logged.
- **Contract test:** `porchlight/sidecar_contract.json` holds synthetic ads and the parser names and identity
  fields they must produce. `porchlight selftest` runs it against the configured binary.

### 4.2 Scanner (Python, bleak)

- Use active scanning, which is bleak's default on BlueZ; local names often arrive only in scan responses.
  Passive scanning on BlueZ needs advertisement-monitor patterns, so it's out of scope.
- Read the address type from BlueZ props the way adwatch does.
- **Verify on the Pi** that a device sitting still keeps producing callbacks, at least every ~10 s. If BlueZ's
  duplicate filtering suppresses them, turn on `DuplicateData` through bleak's BlueZ scanner arguments.
  Measuring dwell time depends on this.
- Optionally tee the scanner JSONL to a capture file (section 4.10) for replay.

### 4.3 Resolver: from ad to identity keys

Each parsed ad yields zero or more **identity keys**. Load the fields table (format in section 10) at
startup.

1. **Payload IDs**
   - `fields` where `source == "meta"`: for each parser result, if `(parser, key)` is listed, `metadata[key]`
     gives the key `id:{parser}:{key}:{value}`.
   - `fields` where `source == "stableKey"`: if the parser is listed, `result.stableKey` gives
     `sk:{parser}:{stableKey}`.
   - `name_families`: take the local name, attributed to each result's parser, or to `unparsed` if nothing
     parsed the ad. If the name starts with a family's `prefix` and the rest contains a token matching
     `rules.name_token_regex`, the key is `name:{parser}:{full name}`.
   - Drop junk values and bad embedded MACs (section 10), skip stable keys with a prefix in
     `rules.skip_stable_key_prefixes`, and skip every parser in `unreliable_parsers`.
   - Use `high` and `medium` confidence rows. `low` rows are opt-in (`identity.include_low_confidence`).
2. **Stable MAC.** If the address is public, or random with the top two bits `11` (random static), add
   `mac:{ADDR}`. Resolvable and non-resolvable private addresses add nothing.
3. **Strength.** Every key gets `bits`, estimated from the value (or from the name tokens) as in section 10,
   and `weak = bits < rules.weak_bits` (24). MAC keys count as 48 bits.
4. **Shared-value guard.** A payload key seen from 3 or more distinct addresses within 60 s is a fleet or
   default value, not a unit. Mark it `shared` (persisted) and ignore it from then on.

Ads that produce no keys still count toward an "N anonymous devices nearby" figure on the page, and toward
nothing else.

### 4.4 Units

- A **unit** is one physical device. Keys seen in the same ad, or from the same address within 10 minutes
  (the same radio), belong to the same unit. Use union-find and persist it in `unit_keys`.
- **Weak keys can join a unit but never merge two existing units.** With a few hundred devices around a
  house, 16-bit tokens collide. A unit whose keys are all weak can still alert, but the alert says
  "weak ID, may be a different device".
- **Unit fields:** vendor, product, ID types, mobility, first and last seen, label, label name, and a 4-character
  hint (section 4.10).
- **Mobility** comes from the matched table row with the best confidence that isn't `unknown`. For MAC-only
  units, use the majority mobility of the table rows for the parsers that matched it. Otherwise it is
  `unknown`.

### 4.5 Visits

- A **visit** is an unbroken presence of one unit: its sightings with gaps of `visit_gap_minutes` (default 5)
  or less.
- Keep the start, end, sighting count, max RSSI and average RSSI.
- Open visits live in memory. Write them to SQLite when they close, plus a checkpoint every 60 s, to spare the
  SD card.
- A visit is **near** when its max RSSI is at least `rssi_floor` (default −80 dBm; tune it, see M4).

### 4.6 Rules

A unit is **known** when it has a label (`household`, `known` or `ignore`) or was auto-baselined (section
4.8). Otherwise it is **unknown**. Each unit's mobility class gives it a weight:

| Weight | Mobility classes |
|---|---|
| high | `vehicle`, `personal`, `in_transit` |
| medium | `unknown` |
| low | `fixed`, `movable` |

| Rule | Fires when | Severity | Repeats |
|---|---|---|---|
| **R1 Lingering stranger** | An unknown unit's current near visit reaches `linger_minutes` (default 10). | `alert` for high or medium weight. Low-weight units only produce an `info` entry ("new fixed device nearby"), which stays on the page and is never pushed. | Once per visit. |
| **R2 Repeat visitor** | An unknown unit, not fixed or movable, had near visits on `repeat_days` (default 3) distinct local days within `repeat_window_days` (default 14). The alert lists the visit times. | `alert` | Once. If acknowledged but not labelled, it fires again only after `repeat_days` more distinct days. |
| **R3 New while armed** | Armed, the unit was never seen before this visit, the visit is near, and it has lasted `armed_min_dwell_seconds` (default 60; 0 fires instantly). Any mobility. | `alert` | Once per unit. |
| **R4 Known at odd hours** | A unit labelled `known` (never `household` or `ignore`), or an auto-baselined unit that isn't fixed or movable, with 5+ past visits on 3+ days, starts a near visit in a local hour with no earlier visit start within ±1 h. Also: any such unit arriving inside optional `quiet_hours`. | `warn` | Once per visit. |

Rule behaviour:
- R1, R2 and R4 run all the time. R3 runs only while armed.
- `ignore` units never alert, and `household` units never alert.
- A per-unit cooldown (`cooldown_minutes`, default 30) applies across all rules.

### 4.7 Arming

The modes, set by `arming.mode`:

| Mode | Behaviour |
|---|---|
| `always` | Always armed. |
| `manual` | A toggle on the page, plus `POST /api/arm`. The state survives restarts. |
| `schedule` | A list of windows, which may cross midnight, e.g. `{days = "mon-fri", from = "08:30", to = "17:30"}`. |
| `presence` | Units labelled `household` act as keys. The house is armed when none has been near for `away_after_minutes` (default 15), and disarmed as soon as one is near. Only units with a key of 24 bits or more (or a stable MAC) can be presence keys, because weak ones collide. The page should say that phones can't be keys, and suggest a watch, car, earbuds or fitness band. |

In every mode, a manual override on the page lasts until the next automatic transition: a schedule edge or a
presence change.

### 4.8 Learning

- For the first `learning_days` (default 7) after install, nothing is pushed. The page lists what *would*
  have alerted, so the thresholds can be tuned.
- When learning ends, these units are auto-baselined:
  - fixed or movable units that had a near visit, which are the neighbours' things;
  - any unit seen on 3 or more distinct days, which are the regulars.
  Everything else stays unknown.
- A "re-learn" button resets the baseline and keeps labels.

### 4.9 Labels and the web page

**Labels** are the main tuning knob. Each has a free-text name.

| Label | Effect |
|---|---|
| `household` | Your own devices. They act as presence keys and never alert. |
| `known` | Neighbours and regular visitors. Only R4 applies to them. |
| `ignore` | Never alerts. |

**The page** is aiohttp serving one static HTML file plus vanilla JS that polls `GET /api/state` every 5 s. No
build step and no framework. It has these sections:
- Armed state, mode and the override toggle.
- Open alerts, which can be acknowledged and labelled from the alert itself.
- **Near now:** product, ID type, mobility, dwell, RSSI and label.
- **Devices:** search, label, and visit history.
- Learning status.
- **About:** parser count, parser commit, uptime, ads/s, and anonymous devices nearby.

Show identifiers masked everywhere, on the page and in notifications: vendor, product, ID type and a
4-character hint ("…3F2A"). Never the full value.

**Access:**
- Binds to `127.0.0.1` by default.
- `web.listen = "0.0.0.0"` is opt-in and then requires `web.token`, either as a bearer token or as a `?token=`
  that sets a cookie.
- LAN only, with no TLS in v1.

### 4.10 Storage (SQLite, WAL)

```
units(id, vendor, product, id_types, mobility, weak, first_seen, last_seen,
      label, label_name, hint, baseline)
unit_keys(key_hmac PRIMARY KEY, unit_id, kind, bits, shared)
visits(id, unit_id, start, end, n, max_rssi, avg_rssi)
alerts(id, unit_id, rule, severity, created, acked, details_json)
state(k PRIMARY KEY, v)          -- armed, override, learning_started, schema version
```

**Identifiers**
- Identity keys are stored only as **HMAC-SHA256(local secret, key)**.
- The secret is generated on first run in `/var/lib/porchlight/secret` (mode 0600). If it's lost, every unit
  is new again; the README should say so.
- The raw values never touch disk. `hint` holds only the last 4 characters.

**Time.** Timestamps are stored in UTC. Days and hours for the rules use the Pi's local time zone.

**Retention**
- Visits and alerts are kept for 180 days.
- Unlabelled units not seen for 90 days are deleted along with their keys.

**Writes** are batched, at least 30 s apart.

**Capture** for debugging is off by default. `debug.capture_jsonl = "<path>"` writes the scanner's JSONL,
rotating daily with a size cap. It is the only raw-identifier store, and it's for tuning only.

### 4.11 Notifiers

- **Interface:** `async def send(alert)`.
- **Configuration:** a list of `[[notify]]` entries, each with a `type` and a `min_severity`.
- **v1:** `page` (always on) and `log` (stdout, which goes to journald).
- **M3:** `ntfy` (an HTTP POST to the topic URL, with an optional token), `webhook` (POSTs the alert JSON), and
  `mqtt` (publishes alerts and the armed state; Home Assistant discovery is optional).
- A failing notifier never blocks the pipeline. Retry a few times, then drop the alert and log it.

### 4.12 Replay mode

`porchlight replay <capture.jsonl> [--speed max|1x]` runs a capture through the whole pipeline with a
simulated clock and no Bluetooth. Tests, threshold tuning and development on the Mac all use it, with a macOS
build of the parser.

## 5. Configuration (`/etc/porchlight/config.toml`, every key optional)

```toml
adapter = "hci0"
db = "/var/lib/porchlight/porchlight.db"
fields = "/opt/porchlight/data/persistent_fields.json"
parser_bin = "/opt/porchlight/bin/ble-parse"

[identity]
include_low_confidence = false

[presence]
rssi_floor = -80
visit_gap_minutes = 5

[rules]
linger_minutes = 10
repeat_days = 3
repeat_window_days = 14
armed_min_dwell_seconds = 60
cooldown_minutes = 30
quiet_hours = ""            # e.g. "00:00-05:00"

[learning]
learning_days = 7

[arming]
mode = "manual"             # always | manual | schedule | presence
away_after_minutes = 15
schedule = [ { days = "mon-fri", from = "08:30", to = "17:30" } ]

[web]
listen = "127.0.0.1"
port = 8080
token = ""

[[notify]]
type = "log"
min_severity = "warn"

[debug]
capture_jsonl = ""
```

## 6. Testing (required: red/green TDD)

**The owner's rule is red/green TDD for everything.** Write each test first, watch it fail, then make it pass.
Say so in the commit or PR notes.

**Fixtures are synthetic only.**
- No real MACs, serials, IMEIs, VINs, device names or places go in the repo. The owner's policy is that model,
  product and protocol information may be public, but anything that identifies one physical device, person or
  place may not.
- Use obviously fake values: `C0:FF:EE:xx:xx:xx` MACs, `TEST0001` serials, and so on.
- The real fields table never goes in the repo either. Tests use the synthetic `tests/fields.json`.

**Unit tests**
- **Resolver:** each source kind; junk values; bad embedded MACs; unreliable parsers; the low-confidence
  toggle; stable-MAC classification of all four address kinds.
- **Units and visits:** the shared-value guard; unit merging, including that weak keys never merge two units;
  visit gap boundaries.
- **Rules:** each one exactly at its thresholds, and the cooldown.
- **Arming:** schedule windows that cross midnight; presence with `away_after`; override expiry.
- **Learning and storage:** learning and baseline; retention.
- **No raw identifiers on disk:** write some, then grep the DB file's bytes for the raw test values.

**Parser contract test.** The synthetic ads in `sidecar_contract.json` go in, and the expected parser names
and keys come out. Run it on the Mac, and on the Pi as an install smoke test (`porchlight selftest`).

**Replay scenarios** (fake clock, from synthetic captures, through a real parser binary; they skip without
one):

| Scenario | Expected |
|---|---|
| A neighbour's fixed devices all week | No alerts. |
| A drive-by at −70 dBm for 20 s | Nothing. |
| A car parked near for 20 min | R1. |
| The same watch on 3 evenings | R2. |
| Armed, and new earbuds near for 2 min | R3. |
| A `known` car at 03:00 when it only ever came 17:00–19:00 | R4. |
| Presence mode: the household watch leaves | Armed after 15 min. |

**On-device acceptance** (manual, written up in the README): 24 h at home on a Zero 2 W, with average total CPU
under 30%, total RSS under 150 MB, and no alert storms.

## 7. Milestones

**M0: Parser on a Pi**
- Run the supplied `ble-parse` on a Pi.
- Pass the contract test, and measure throughput and RSS.

**M1: Pipeline to storage**
- Scanner, then parser, then resolver, then units and visits in SQLite.
- `porchlight status` prints the units near now, and replay mode works.

**M2: The alarm**
- Rules, labels, learning, all four arming modes, the web page, and the `page` and `log` notifiers.
- A systemd unit, `deploy/install.sh` and `config.example.toml`.

**M3: More notifiers.** ntfy, webhook, and MQTT for Home Assistant.

**M4 (optional): Tuning helpers**
- An RSSI calibration view ("walk to the curb wearing your watch and read the number").
- Per-rule counts of what would have fired.

## 8. Non-goals for v1

- Multiple sensors.
- Any cloud or upload of any kind.
- GPS.
- Phone detection by resolving IRKs.
- Unwanted-tracker detection.
- Cameras.
- User accounts.

**Never connect to a device.** The system only receives; no GATT.

## 9. Identity lessons (don't regress)

- **Shared values.** A value broadcast by 3 or more radios at once is a fleet or default value, not a unit.
  So are all-zero and all-F values, including inside stable keys: strip the `parser:` prefix before the junk
  check.
- **Weak tokens.** IDs under 24 bits (a 4-hex MAC tail, a 16-bit name suffix) collide in a busy
  neighbourhood, so they must never merge units.
- **Unreliable parsers.** Some parsers get identity wrong: one re-mints part of its ID per address, one keys
  every zeroed frame to one ID, one keys on the model name. The table lists them in `unreliable_parsers`, and
  the resolver skips them. Add others if replay shows the same pattern.
- **Same radio.** Merge on the same radio: values seen on one address at the same time belong to the same
  device. This is how a speaker's device ID, its stable key and its name suffix become one unit, and how a
  device's name joins its unit whichever parser claims it.
- **What moves matters most.** Many devices with persistent IDs are on things that move (vehicles, above all,
  and worn or carried devices), and most of those carry an ID of 48 bits or more. A fixed device only reveals
  a place that is already known; mobile ones follow a person. That is why the rules weight mobility.
- **Most devices pass once.** Expect a long tail of one-off passers-by, and keep the dwell and RSSI gates in
  front of every alert.
- **Unparsed names are risky.** A local name with no parser behind it is an identity only through the
  table's `unparsed` families, which have prefixes of 3 or more characters. Don't generalise to "any name
  with a hex run": rotating name tokens would turn every rotation into a "new device".

## 10. The fields table (`persistent_fields.json`)

Supplied with the parser. It contains no free text and no observed values: only parser names, key names,
name prefixes and classes. Its top-level keys:

| Key | Contents |
|---|---|
| `fields` | Rows of `{source: "meta" or "stableKey", parser, key, id_type, confidence, vendor, product, category, mobility}`. |
| `name_families` | Rows of `{parser, prefix, id_type, confidence, vendor, product, mobility, min_token_bits}`. `parser` may be `unparsed`. |
| `unreliable_parsers` | Parsers whose identity must never be trusted. |
| `rules` | `weak_bits` (24), `shared_if_concurrent_addresses` (3), `name_token_regex`, and `skip_stable_key_prefixes`. |

`confidence` is `high`, `medium` or `low`. `mobility` is one of `fixed`, `movable`, `personal`, `vehicle`,
`in_transit` or `unknown`. Parser fields that aren't in the table are simply not identities.

The value rules, which must match the ones the table was built with:
- **Junk:** no alphanumerics, all 0, all F, or one repeated character, after stripping separators. For stable
  keys, first strip leading word-only segments (`sonos:`, `mac:`); a two-hex-digit segment is a MAC octet,
  not a word.
- **Bad embedded MAC:** for MAC-like keys (`mac`, `bd_addr`, `embedded_address`, `device_address`), a 12-hex
  value with 4 or more zero octets, or with the multicast bit set in both the first and the last octet.
- **Bits:** summed over alphanumeric tokens: 3.32 bits per character for digits only, 4 for hex, 5.17 for
  anything else.

## 11. Layout

```
porchlight/                # in the adwatch repo
  SPEC.md
  README.md
  porchlight/              # Python: config, scanner, sidecar, resolver, units, visits,
                           #   rules, arming, learning, store, notify/, web/, cli
  tests/                   # including fields.json, the synthetic table
  deploy/                  # porchlight.service, install.sh, config.example.toml
  scripts/bench_parser.py
```

`.gitignore` must cover `*.db`, captures, `secret`, `bin/` (the parser) and `data/` (the real table).
