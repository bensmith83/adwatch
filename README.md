# adwatch

BLE advertisement analyzer. Passively scans for Bluetooth Low Energy advertisements, classifies them, parses known protocols via a plugin system, stores everything in SQLite, and presents results through a real-time web dashboard.

## Quick Start

```bash
# Create venv and install
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# Run with dashboard (default)
adwatch

# Dashboard will be at http://localhost:8080
```

## Usage

```bash
adwatch                              # Start scanner + dashboard
adwatch --no-dashboard               # Scanner only, log to stdout
adwatch --adapter hci1               # Use specific BLE adapter
adwatch --db ./my.db                 # Custom database path
adwatch --port 9090                  # Custom dashboard port
adwatch --host 127.0.0.1             # Bind to localhost only
adwatch --list-plugins               # Show loaded plugins and exit
adwatch --disable thermopro,matter   # Disable specific plugins
```

## Environment Variables

All options can also be set via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `ADWATCH_ADAPTER` | `hci0` | BLE adapter |
| `ADWATCH_DB_PATH` | `./adwatch.db` | SQLite database path |
| `ADWATCH_HOST` | `0.0.0.0` | Dashboard bind address |
| `ADWATCH_PORT` | `8080` | Dashboard port |
| `ADWATCH_RAW_RETENTION_DAYS` | `7` | Raw advertisement retention |
| `ADWATCH_PARSED_RETENTION_DAYS` | `30` | Parsed data retention |
| `ADWATCH_LOG_LEVEL` | `INFO` | Logging level |
| `ADWATCH_DISABLED_PLUGINS` | | Comma-separated plugin names to disable |

## Parsers

13 parsers ship built-in (9 core + 4 plugins):

**Core parsers** (always loaded):
- Apple: Continuity/Nearby, AirDrop, Find My, Proximity (AirPods), AirPlay, Nearby Action
- iBeacon
- Google Fast Pair
- Microsoft CDP

**Plugins** (can be disabled):
- ThermoPro temperature/humidity sensors
- Matter commissioning
- Tile trackers
- Samsung SmartTag

## Running Tests

```bash
source venv/bin/activate
python -m pytest tests/ -v
```

## Dashboard

The web dashboard at `http://<host>:<port>` provides:
- Summary cards showing device counts by category
- Live feed of incoming advertisements (WebSocket-powered)
- Plugin-specific tabs (e.g. ThermoPro sensor readings)

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/overview` | Summary counts by category |
| GET | `/api/feed?limit=100` | Recent advertisements |
| GET | `/api/raw?mac=XX&type=YY&since=ZZ` | Query raw ads with filters |
| GET | `/api/plugins` | List loaded plugins |
| GET | `/api/plugins/ui` | Plugin UI configurations |
| WS | `/ws` | WebSocket for real-time events |

## Requirements

- Python 3.11+
- Bluetooth adapter (for scanning)
- Linux with BlueZ (for BLE access)
