# ThermoPro BLE Sensor Plugin

## Overview

ThermoPro wireless temperature/humidity sensors (TP357S, TP359S, TP351S) broadcast readings via BLE advertisements. They use a non-standard encoding that embeds part of the temperature value inside the BLE `company_id` field, which normally identifies the manufacturer.

adwatch parses these advertisements to provide a live sensor dashboard with temperature, humidity, room speculation, and user-assignable nicknames.

## Supported Models

| Model   | Model Byte | Notes                    |
|---------|-----------|--------------------------|
| TP357S  | `0x0B`    | Indoor thermometer       |
| TP359S  | `0x13`    | Indoor thermometer       |
| TP351S  | `0x33`    | Indoor thermometer       |

Additional models may work if they follow the same protocol. The parser falls back to extracting the model name from `local_name` if the model byte is unrecognized.

## BLE Advertisement Format

### Identification

ThermoPro sensors are identified by their BLE `local_name`, which follows a stable pattern:

```
TP357S (1234)
TP359S (5678)
TP351S (9012)
```

Regex: `^(TP\d{3}[A-Z]?)\s*\(([\dA-Fa-f]{4})\)$`

- Group 1: Model name (e.g. `TP357S`)
- Group 2: 4-character unit identifier (stable per physical device)

The `local_name` is the **stable sensor identity** — it does not change across readings and survives MAC address rotation. The MAC address is NOT used for identity (it rotates).

### Company ID Quirk

ThermoPro uses BLE company ID `0x__C2` where the high byte varies per reading. This is non-standard — normally `company_id` is a fixed vendor identifier. ThermoPro repurposes the high byte to carry `temp_lo` (the low byte of the temperature value).

The BLE scanner stores manufacturer data as `company_id.to_bytes(2, 'little') + data`, so the full payload available for parsing is 7 bytes.

### Manufacturer Data Layout (7 bytes)

```
Byte 0: 0xC2        — ThermoPro marker (low byte of company_id, constant)
Byte 1: temp_lo     — Temperature low byte (high byte of company_id — varies!)
Byte 2: temp_hi     — Temperature high byte
Byte 3: humidity    — Relative humidity (unsigned 8-bit, 0–100%)
Byte 4: unknown     — Purpose unknown (always observed as 0x00)
Byte 5: model_code  — Device model identifier (see table above)
Byte 6: status      — Status byte (always observed as 0x01)
```

### Temperature Decoding

Temperature is encoded as a **signed 16-bit integer** in tenths of a degree Celsius:

```
raw_value = (temp_hi << 8) | temp_lo     # unsigned 16-bit assembly
if raw_value >= 0x8000:
    raw_value -= 0x10000                  # convert to signed
temperature_c = raw_value / 10.0
```

**Examples:**

| temp_hi | temp_lo | raw (hex) | raw (signed) | Temperature |
|---------|---------|-----------|-------------|-------------|
| `0x00`  | `0xD7`  | `0x00D7`  | 215         | 21.5°C      |
| `0x01`  | `0x0E`  | `0x010E`  | 270         | 27.0°C      |
| `0x00`  | `0x00`  | `0x0000`  | 0           | 0.0°C       |
| `0xFF`  | `0xCE`  | `0xFFCE`  | -50         | -5.0°C      |
| `0xFF`  | `0x9C`  | `0xFF9C`  | -100        | -10.0°C     |

### Humidity

Byte 3 is a straightforward unsigned 8-bit relative humidity percentage (0–100).

## Sensor Identity & Hashing

The identifier hash is derived from the `local_name` (NOT the MAC address):

```
hash = SHA256("thermopro:{local_name}")[:16]
```

This means:
- Same physical sensor always produces the same hash, regardless of which MAC it's advertising from
- Two different sensors (e.g. `TP357S (1234)` vs `TP357S (9999)`) produce different hashes
- Temperature/humidity readings do NOT affect the hash — it's purely identity-based

## Room Speculation

The parser includes a heuristic room-type guesser based on temperature and humidity:

| Condition                        | Speculation          |
|----------------------------------|----------------------|
| temp < -10°C                     | Freezer              |
| -10°C ≤ temp < 2°C              | Fridge               |
| 2°C ≤ temp < 10°C               | Garage/Unheated      |
| 18–24°C, humidity < 35%         | Indoor (dry/heated)  |
| 18–24°C, humidity 35–55%        | Indoor (comfortable) |
| 18–24°C, humidity > 55%         | Bathroom/Kitchen     |
| temp > 30°C                      | Attic/Hot area       |
| Everything else                  | Outdoor/Unknown      |

This is displayed as a badge on the sensor card. User-assigned nicknames override the display name but the speculation is always shown.

## Implementation Files

| File | Purpose |
|------|---------|
| `src/beacon_parser.py` | `parse_thermopro()`, `speculate_room()`, `THERMOPRO_LOCAL_NAME_RE`, `THERMOPRO_MODEL_CODES` |
| `src/models.py` | `ThermoProSighting` dataclass |
| `src/storage/thermopro_storage.py` | `ThermoProRepository` — sightings + nickname CRUD |
| `src/storage/migrations.py` | `thermopro_sightings` and `sensor_nicknames` tables |
| `src/orchestrator.py` | Wiring: parse → save → emit `thermopro_reading` WebSocket event |
| `src/dashboard/routers/thermopro.py` | API endpoints under `/api/thermopro/` |
| `src/dashboard/static/thermopro.html` | Dashboard page at `/sensors` |
| `tests/test_thermopro_parser.py` | 22 parser tests |
| `tests/test_thermopro_storage.py` | 10 storage tests |
| `tests/test_thermopro_api.py` | 5 API tests |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/thermopro/active?timeout_minutes=5` | Latest reading per sensor within timeout window |
| GET | `/api/thermopro/history/{sensor_id}?hours=24` | Time series for one sensor |
| PUT | `/api/thermopro/nickname` | Set nickname (JSON: `{sensor_id, nickname}`) |
| DELETE | `/api/thermopro/nickname/{sensor_id}` | Remove nickname |

## Database Schema

```sql
CREATE TABLE thermopro_sightings (
    id INTEGER PRIMARY KEY,
    timestamp TEXT NOT NULL,
    mac_address TEXT NOT NULL,
    sensor_id TEXT NOT NULL,
    model_code TEXT NOT NULL,
    temperature_c REAL NOT NULL,
    humidity INTEGER NOT NULL,
    room_speculation TEXT NOT NULL,
    identifier_hash TEXT NOT NULL,
    rssi INTEGER,
    raw_payload_hex TEXT
);

CREATE TABLE sensor_nicknames (
    sensor_id TEXT PRIMARY KEY,
    nickname TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

## Dashboard Behavior

- Default temperature display: **Fahrenheit** (primary), Celsius (secondary)
- On page load: fetches active sensors (5min window); if empty, falls back to 60min window with stale indicator (dashed border, reduced opacity, "(stale)" label)
- Auto-refresh every 30 seconds via fetch
- Real-time updates via WebSocket `thermopro_reading` event
- Click sensor name to inline-edit nickname (blur/Enter saves, Escape cancels)
- Navigation: "Environment > Sensors" in the nav bar across all pages

## Raw Packet Examples

```
# 21.5°C, 55% humidity, TP357S
c2 d7 00 37 00 0b 01
│  │  │  │  │  │  └── status (always 0x01)
│  │  │  │  │  └───── model code (0x0B = TP357S)
│  │  │  │  └──────── unknown
│  │  │  └─────────── humidity (0x37 = 55%)
│  │  └────────────── temp_hi (0x00)
│  └───────────────── temp_lo (0xD7)
└──────────────────── marker (0xC2)

temp = signed_16(0x00D7) / 10 = 215 / 10 = 21.5°C

# -5.0°C, 70% humidity, TP359S
c2 ce ff 46 00 13 01
temp = signed_16(0xFFCE) / 10 = -50 / 10 = -5.0°C
```
