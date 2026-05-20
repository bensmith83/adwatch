# Unknown T-Series BLE Device Family Plugin

## Overview

A family of BLE devices observed in a 2026-05-19 scan sharing a custom 128-bit service UUID and a distinctive local-name pattern, but for which **the vendor could not be identified** from public sources.

Three distinct devices appeared in the capture, each advertising for the full scan window (92-96 sightings):

| Local name | Sightings | Address type |
|---|---|---|
| `T59024E4` | 96 | random |
| `T09025E1` | 92 | random |
| `T5902907` | 95 | random |

All three advertise exactly one custom service UUID — `72D53E62-E515-452E-9416-5F4392F27701` — and no manufacturer data, no service data. The local-name pattern is `T` followed by exactly 7 uppercase hex characters, which is plausibly a hardware-serial-derived broadcast name.

The UUID is **not** registered in [NordicSemiconductor/bluetooth-numbers-database](https://github.com/NordicSemiconductor/bluetooth-numbers-database) (`v1/service_uuids.json`), and no public GitHub code search, Google search, or Bluetooth SIG directory hit returns any reference to it. The 7-hex-char serial pattern is consistent with what cheap OEM Chinese fitness / asset-tracker SDKs typically emit, but **we cannot confidently attach a vendor**, so the parser is deliberately named `unknown_t_series` and does **not** surface a `vendor` field. Future identification (e.g. by visually observing a labelled device in the wild) can attach one without breaking the stable-key contract.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Service UUID (128-bit, custom) | `72D53E62-E515-452E-9416-5F4392F27701` |
| Local name | `T<HEX7>` — capital `T` followed by exactly 7 uppercase hex characters, e.g. `T59024E4` |
| Manufacturer data | none |
| Service data | none |
| Address type | random (rotates) |

### Local Name Format

```
T59024E4
│└──┬───┘
│   └── 7-char uppercase hex serial — assumed device-unique
└────── literal 'T' family marker
```

The parser extracts the 7-char hex tail as `serial` and scopes the stable key to it: `unknown_t_series:<SERIAL>`. This collapses repeated MAC rotations of the same physical device into a single key (the underlying BD_ADDR is random and rotates, so the serial-in-the-name is the only stable identifier we have).

## Detection Significance

- **The UUID + name pattern is highly specific.** A 128-bit custom UUID combined with the `T<HEX7>` name pattern is unlikely to collide with another vendor — three devices in one scan all hitting both is strong evidence of a single device family.
- **MAC-rotation tolerant.** Because we anchor on the serial inside the local name, sightings of the same physical device across MAC-randomisation events deduplicate cleanly.
- **Provides a hook for later identification.** Even unidentified, surfacing the family lets us flag, count, and later annotate these devices once the vendor is identified (e.g. by correlating with a labelled device in a controlled scan).

## What We Cannot Parse

- **Vendor / model line.** No manufacturer data, no service data, no published documentation. We document this as `unknown_t_series` and decline to invent a vendor.
- **Telemetry.** All payload is in the (presumed) GATT characteristics behind the custom service — not in the advertisement.
- **Firmware / hardware version.** Not advertised.

## References

- `research/adwatch_export 6.json` — the three captured devices (local entries: `T59024E4`, `T09025E1`, `T5902907`)
- [NordicSemiconductor/bluetooth-numbers-database — `v1/service_uuids.json`](https://github.com/NordicSemiconductor/bluetooth-numbers-database/blob/master/v1/service_uuids.json) — checked 2026-05-20; UUID `72D53E62-E515-452E-9416-5F4392F27701` is not present
- GitHub code search for `72D53E62-E515-452E-9416-5F4392F27701` — no public results as of 2026-05-20
- Google search for the bare UUID — no public results as of 2026-05-20
