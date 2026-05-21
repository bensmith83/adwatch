# RingConn Plugin

## Overview

**RingConn** is a Shenzhen-based smart-ring brand competing with Oura, Ultrahuman, and Samsung's Galaxy Ring. The ring is a sensor-laden titanium band worn on the finger; the companion **RingConn** mobile app (iOS / Android) syncs continuous biometric data and surfaces readiness, sleep, sleep-apnea, and AI-coach insights. Unlike most of its subscription-bound rivals, app access is included with the hardware.

Two product generations have shipped to date (Gen 3 was announced at CES 2026 but is not yet present in our captures):

| Generation | Launched | Marketing name | Local-name form |
|---|---|---|---|
| Gen 1 | 2023 | RingConn Smart Ring | `RingConn-XXXX` |
| Gen 2 | 2024 | RingConn Gen 2 (ultra-light, 12-day battery) | `RingConn Gen2-XXXX` |

The ring measures: heart rate, HRV, SpO2, skin temperature, sleep stages, sleep apnea index, and step count. The case doubles as a wireless charger.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Manufacturer data | absent (RingConn has no published SIG company ID) |
| Service UUIDs | absent on the GAP advertising channel (proprietary service is exposed only after connect) |
| Service data | absent |
| Local name | `"RingConn-XXXX"` (Gen 1) or `"RingConn Gen2-XXXX"` (Gen 2) |

`XXXX` is the last four hex characters of the ring's BLE MAC address (uppercase), a convention also used by Whoop, COROS, and Garmin smart-watch series. The trailing hex token is the only per-device signal — there is no rotating identifier or counter.

Because the local name is the only on-air signal, we match strictly on the name pattern:

```
^RingConn(?: Gen[12])?-[0-9A-Fa-f]{4}$
```

The pattern is specific enough that false positives from unrelated devices are unlikely. We deliberately refuse Gen-3 (`Gen3`) and other unknown generation tokens until we have a confirmed capture.

### Device-Class Heuristic

All matching advertisements surface `device_class = smart_ring`. Metadata always includes:

| Key | Value |
|---|---|
| `vendor` | `RingConn` |
| `product_family` | `smart ring` |
| `generation` | `"1"` (Gen 1) or `"2"` (Gen 2) |
| `mac_suffix` | the captured 4-char hex token |
| `device_name` | the full observed local name |

The stable key is `ringconn:<localName>`.

## Examples

| Capture | Inference |
|---|---|
| local name `"RingConn Gen2-6DD7"` (only signal) | generation = 2, mac_suffix = `6DD7`, class = `smart_ring` |
| local name `"RingConn-AB12"` | generation = 1, mac_suffix = `AB12`, class = `smart_ring` |
| local name `"RingConn Gen2-abcd"` | generation = 2, mac_suffix = `abcd` (case-insensitive) |
| local name `"RingConn"` (no suffix) | no match |
| local name `"RingConn Gen3-1234"` | no match (unknown generation; pending capture) |

## References

- [RingConn Gen 2 product page](https://ringconn.com/products/ringconn-gen-2)
- [RingConn Gen 2 quick-start guide](https://ringconn.com/pages/ringconn-gen-2-quick-guide)
- [RingConn smart ring setup guide](https://www.smartphoneassistant.com/smart-ring/getting-started/ringconn-smart-ring-setup/)
- [RingConn Gen 3 launch coverage (CES 2026)](https://www.gizmochina.com/2026/05/05/ringconn-gen-3-smart-ring-launched-specs-price/)
