# Unidentified BLE Beacons (Observation Log)

Captures of BLE advertisements adwatch cannot yet attribute. Documented here
so future exports + external research can close the gaps.

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

## OVAT5-K0194559 — Local Name Only

Observed 2026-04-18 around 17:01 UTC (6 sightings, rssi -92 dBm).

| Field | Value |
|-------|-------|
| `local_name` | `OVAT5-K0194559` |
| `service_uuids` | *(empty)* |
| `manufacturer_data` | *(empty)* |
| `service_data` | *(empty)* |
| address type | random |

The name format `OVAT5-K0194559` looks like `<model>-<serial>` where `OVAT5`
is a 5-character product code and `K0194559` is a 7-digit serial prefixed
with `K`. The ad carries no payload beyond the name (random-address
connectable beacon — likely a device waiting to be paired).

No matching SKU found in public product databases. The signal is weak
(-92 dBm max) so this was almost certainly observed as a drive-by / neighbor
and may not repeat.

**Action:** if re-observed at close range, attempt a GATT connect to read the
Device Information service (0x180A) for manufacturer / model strings.

## Tracking

When new identifications emerge for any of the above, migrate the entry out
of this file into a dedicated `docs/protocols/<name>.md` and (if the protocol
is decodable) implement a plugin under `src/adwatch/plugins/`.
