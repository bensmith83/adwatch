# Unidentified BLE Beacons (Observation Log)

Captures of BLE advertisements adwatch cannot yet attribute. Documented here
so future exports + external research can close the gaps.

## NJXAS — Service UUID `0xFEAF`

Observed continuously since 2026-03-19. Single persistent emitter with 4273+
sightings.

| Field | Value |
|-------|-------|
| `local_name` | `NJXAS` |
| `service_uuids` | `["FEAF"]` |
| `service_data[FEAF]` | `1001000200e11900546313520066166401` (17 bytes) |
| address type | random |

**FEAF** is *Nest Labs Inc.* in the Bluetooth SIG assigned-numbers registry
(Nest is now owned by Google). Structure of the 17-byte service data:

```
10 01 00 02 00 e1 19 00 54 63 13 52 00 66 16 64 01
│  │  │     │     │                 │  ...
│  │  │     │     └── appears to change over time (24-bit counter?)
│  │  │     └──────── 0x00 0x02 — fixed
│  │  └────────────── 0x00 — fixed
│  └───────────────── 0x01 — frame / version
└──────────────────── 0x10 — magic
```

"NJXAS" doesn't match a known Nest product SKU. Guess: a research /
pre-production Nest device or a third-party vendor reusing FEAF. If this is a
resident Nest thermostat, Nest Cam, or Nest Hub, the stable local name makes
it easy to fingerprint.

**Action:** capture longer service-data time series to see which bytes vary.

## W600N — Service UUID `0xFE79`

Observed 2026-04-14 01:14 UTC (9 sightings in a short burst).

| Field | Value |
|-------|-------|
| `local_name` | `W600N` |
| `service_uuids` | `["FE79"]` |
| service_data | *(empty)* |

**FE79** is *Zebra Technologies Corp* in the Bluetooth SIG registry — the
industrial barcode-scanner / handheld-terminal vendor. "W600N" doesn't match
a known Zebra SKU exactly, but Zebra's MC-series and TC-series handhelds and
the Zebra "Workforce Connect" push-to-talk radios all advertise FE79.

Best guess: an enterprise Zebra handheld radio. See `getac-barcode.md` and
`zebra.md` for related industrial devices already covered by adwatch.

## S201… — Service UUID `0x1122`

Observed continuously since 2026-04-05 (598+ sightings).

| Field | Value |
|-------|-------|
| `local_name` | `S201b91dbacb104cdC` (18 chars, mixed case with middle hex) |
| `service_uuids` | `["1122"]` |
| service_data | *(empty)* |

Service UUID `0x1122` is **not** in the Bluetooth SIG assigned-numbers
registry — it is a non-registered 16-bit UUID that the device is using
privately (technically a spec violation: only 128-bit UUIDs are allowed for
non-assigned service identifiers). Pattern `S201` + 12 hex chars + `C`
suggests the hex block is a MAC address or serial embedded in the name.

Guess: an IoT gateway / ESP32-based hobby project or a cheap tracker using
the SDK's default UUID without requesting a real one.

## Tracking

When new identifications emerge for any of the above, migrate the entry out
of this file into a dedicated `docs/protocols/<name>.md` and (if the protocol
is decodable) implement a plugin under `src/adwatch/plugins/`.
