# Unknown BLE Family — Vendor UUID `DBC6B52C-810F-40E1-B316-BB5D94C275F7`

## Overview

A previously-uncatalogued BLE device family advertising on a vendor-defined
128-bit service UUID, with the local name `Passive`. No public reference
(general web search, GitHub code search, Nordic `bluetooth-numbers-database`,
Theengs / OpenMQTTGateway) attributes the UUID to any brand, datasheet, SDK,
or integration. The family is catalogued here as `vendor: Unknown` with a
fingerprint-only parser so the emitter can be counted now and annotated later
when a labelled specimen turns up.

The signature is **real and recurring**: besides the AdWatch capture, the
identical UUID appears in an independent third-party passive BLE scan log
(`harutiro/jupyter`, an indoor-localization experiment, Feb 2024) as a
strong, persistent beacon (RSSI ~−91…−94) — confirming it is a genuine,
stationary device, not a capture artifact.

## Fingerprint

### Service UUID

| UUID | Notes |
|------|-------|
| `DBC6B52C-810F-40E1-B316-BB5D94C275F7` | vendor-defined 128-bit; often **listed twice** in the same advertisement (duplicated AD structure — harmless; gate on presence, not count) |

The UUID is **not** a UUIDv1 vanity artifact and carries no decodable
embedded OUI/timestamp — it is an opaque vendor identifier.

### Local Name

| Value | Notes |
|-------|-------|
| `Passive` | constant across the observed device |

`Passive` *suggests* a passive-infrared / occupancy / presence sensor, but
this is a **hypothesis, not a confirmed function** — "passive" is also
generic BLE-scanner terminology (passive scanning mode), and the name could
be a firmware default. The parser surfaces this as a clearly-flagged,
unconfirmed `function_hypothesis` and never asserts a function or vendor.

### Other Signals

- No manufacturer data.
- No service data.
- Address type `random`.

## Identification

- **Primary:** service UUID `DBC6B52C-810F-40E1-B316-BB5D94C275F7`
  (case-insensitive — CoreBluetooth emits 128-bit UUIDs uppercase).
- **Device class:** `unknown` — fingerprint-only.

## What We Can Surface

| Field | Source | Notes |
|-------|--------|-------|
| Family flag | service UUID | "we've seen this family before" |
| `local_name` | advertisement | `Passive` |
| `function_hypothesis` | inferred | presence-sensor guess, **flagged unconfirmed** |
| `service_uuid` | advertisement | the 128-bit family UUID |

## What We Cannot Surface

- Vendor / brand / product — no labelled specimen found.
- Confirmed device function (presence sensor vs beacon vs accessory).
- Any telemetry — the advertisement carries no manufacturer/service data.

## Stable Identity

The UUID identifies the *family*; the local name disambiguates a unit. The
on-air address is random, so identity anchors on UUID + name:

```
stable_key = unknown_dbc6b52c:<local_name or "(nameless)">
identifier = SHA256(stable_key)[:16]
```

## References

- Independent capture of the same UUID (no product attribution) —
  <https://github.com/harutiro/jupyter> (`BLE.csv` scan logs)
- Bluetooth SIG Assigned Numbers (128-bit UUIDs are vendor-chosen, not
  registered) — <https://www.bluetooth.com/specifications/assigned-numbers/>
- Companion "vendor unconfirmable, family catalogued" parsers in this
  codebase: `Unknown65333333Parser`, `UnknownD30F3C56Parser`
- Parser: `Sources/Parsers/UnknownDBC6B52CParser.swift`
