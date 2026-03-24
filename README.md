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
adwatch --list-plugins               # Show loaded plugins and exit
adwatch --disable thermopro,matter   # Disable specific plugins
adwatch --listen-network             # Listen on all interfaces (0.0.0.0)
```

## Environment Variables

All options can also be set via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `ADWATCH_ADAPTER` | `hci0` | BLE adapter |
| `ADWATCH_DB_PATH` | `./adwatch.db` | SQLite database path |
| `ADWATCH_HOST` | `127.0.0.1` | Dashboard bind address |
| `ADWATCH_PORT` | `8080` | Dashboard port |
| `ADWATCH_RAW_RETENTION_DAYS` | `7` | Raw advertisement retention |
| `ADWATCH_PARSED_RETENTION_DAYS` | `30` | Parsed data retention |
| `ADWATCH_LOG_LEVEL` | `INFO` | Logging level |
| `ADWATCH_DISABLED_PLUGINS` | | Comma-separated plugin names to disable |

## Parsers

81 parsers ship built-in (9 core + 72 plugins):

**Core parsers** (always loaded):
- Apple: Continuity/Nearby, AirDrop, Find My, Proximity (AirPods), AirPlay, Nearby Action
- iBeacon
- Google Fast Pair
- Microsoft CDP

**Plugins** (can be disabled):
- Sensors: ThermoPro, Ruuvi, Qingping, Inkbird, Tilt, BTHome, MiBeacon, SwitchBot, TPMS, Aranet4, Airthings, ATC/PVVX, BlueMaestro, Efento, SensorPush, Sensirion, SmartDry, ThermoBeacon, Moat, Mopeka, RadonEye, Renpho, Xiaogui Scale, Mi Scale
- Trackers: Tile, Samsung SmartTag, Google Find My Device, Exposure Notification, Chipolo, Nutale, Jaalee, MikroTik Tag, Minew
- Beacons: AltBeacon, Eddystone, Estimote, BT Mesh, Matter, iNode Energy, ELA Innovation, Smart Sensor Devices, Teltonika Eye, NodOn NIU
- Audio: Sonos, Bose, Sony Audio, Samsung Galaxy Buds, Jieli Audio
- Smart Home: Govee, Hatch, Nest, Ember Mug, SwitchBot, ELK-BLEDOM, Philips Sonicare, Kegtron, iBBQ, Meater
- Automotive: Rivian, TPMS, Victron Energy
- TV/Media: LG TV, Samsung TV, Amazon Fire TV, Apple AirPlay
- Other: Oral-B, Flipper Zero, Smart Glasses, GE Appliances, August/Yale, BM2 Battery, Amphiro, UniFi Protect, Google Android Nearby, ENOcean, NoDoN NIU

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
- Protocol Explorer for browsing, filtering, and comparing raw advertisements
- HexViewer with field editor for reverse-engineering unknown BLE payloads
- Protocol Specs: save field definitions, auto-match to ads, generate parser code

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/overview` | Summary counts by category |
| GET | `/api/feed?limit=100` | Recent advertisements |
| GET | `/api/raw?mac=XX&type=YY&since=ZZ` | Query raw ads with filters |
| GET | `/api/plugins` | List loaded plugins |
| GET | `/api/plugins/ui` | Plugin UI configurations |
| GET | `/api/explorer/ads` | Browse ads with filters |
| GET | `/api/explorer/facets` | Filter facets (types, company IDs, UUIDs) |
| GET | `/api/explorer/compare?ids=1,2,3` | Byte-level ad comparison |
| POST | `/api/explorer/specs` | Create protocol spec with fields |
| GET | `/api/explorer/specs/{id}/codegen` | Generate parser plugin from spec |
| WS | `/ws` | WebSocket for real-time events |

## Security

The dashboard has **no authentication**. By default it binds to `127.0.0.1` (localhost only). Use `--listen-network` to expose on all interfaces — only do this on trusted networks.

The `adwatch.db` database contains real BLE advertisement data from your environment (MAC addresses, device names, signal patterns). It is git-ignored by default — do not commit it to a public repository.

## Contributing

If you use the Protocol Explorer to reverse-engineer a new BLE protocol and build a parser plugin for it, please contribute it back! Open a PR with your plugin — the more parsers we have, the more useful adwatch becomes for everyone.

## Requirements

- Python 3.11+
- Bluetooth adapter (for scanning)
- Linux with BlueZ (for BLE access)
