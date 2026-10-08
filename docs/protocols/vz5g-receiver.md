# "VZ5G_RECEIVER" self-identifying frames (service data 0x2A37)

## Overview

Eight distinct units (12 records, 50 sightings) captured 2026-08-26,
2026-09-27 and 2026-10-02 broadcast a service-data frame under `0x2A37`
whose entire 20-byte payload is ASCII: the self-label `VZ5G_RECEIVER_`
followed by a 6-digit per-unit serial. No local name, no manufacturer
data — the frame *is* the device's name.

`0x2A37` is the SIG **Heart Rate Measurement** *characteristic* UUID. The
device misuses a characteristic UUID as a service-data key, which is why
identification must key on the ASCII grammar, not the UUID: a genuine
heart-rate sensor emits a short binary measurement under that key and can
never match a 20-byte ASCII label.

The first unit was logged by the 2026-08-28 sweep (one record,
`VZ5G_RECEIVER_369460`) and deferred at n=1; the 2026-10-05 nightly sweep
found seven more units and shipped the parser (`VZ5GReceiverParser`,
`vz5g_receiver`).

| Unit serial | Capture days | Sightings | RSSI |
|-------------|--------------|-----------|------|
| 288785 | 2026-10-02 | 10 | −88..−100 |
| 531994 | 2026-10-02 | 20 | −70..−91 |
| 934199 | 2026-10-02 | 14 | −84..−102 |
| 305093 | 2026-09-27 | 2 | −92 |
| 618693 | 2026-09-27 | 1 | −87 |
| 518026 | 2026-10-02 | 2 | −103 |
| 369460 | 2026-08-26 | 1 | −92 |

(Plus duplicate records of units already counted; random addresses
throughout.)

## Supported models

Unknown. The label reads as a **5G fixed-wireless receiver** ("VZ"
suggests Verizon 5G Home); see the attribution note — no vendor or
carrier is claimed.

## BLE advertisement format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service data | under `0x2A37`, exactly 20 bytes, matching `^VZ5G_RECEIVER_[0-9]{6}$` | the exact ASCII grammar IS the gate |
| Manufacturer data | none | |
| Local name | none | |
| Address | random | |

### Byte map

```
[0..14)   "VZ5G_RECEIVER_"   ASCII self-label (constant)
[14..20)  6 ASCII digits     per-unit serial (e.g. "288785")
```

Real frame (unit 288785): `565a35475f52454345495645525f323838373835`.

## Identity hashing

```
stableKey      = "vz5g_receiver:<6-digit serial>"   (payload-derived)
identifierHash = SHA256(stableKey)[:16]
```

The serial is the unit's own label, broadcast raw on every frame — a
burned-in per-unit identifier, tagged `.uniqueStable` (the privacy tag
that keeps it out of telemetry uploads).

## Parser scope

Passive-only. The parser claims exactly the 20-byte grammar above and
reports the serial; nothing else in the frame exists to decode.

## What we cannot parse

- The vendor/carrier (see below)
- Whether a second frame family (the IMEI-bearing 0xC001 service-data
  frame recorded on bead gx8b) comes from the same units — the two were
  never co-sighted
- Any state or telemetry

## Detection significance

A sighting means a self-labelled "VZ5G" fixed-wireless receiver is within
BLE range and broadcasting a permanent serial number in the clear — the
privacy pattern NearSight exists to surface.

## Confidence / attribution

**Vendor: unattributed (honest).** The device labels itself
"VZ5G_RECEIVER". That string and the SIG-namespace misuse are the entire
evidence; the "Verizon 5G Home" reading is plausible but circumstantial,
so the parser names no vendor.

**Frame decode: high** for what little there is — the grammar is
byte-exact across 12 records.

## References

- Bluetooth SIG `service_uuids.yaml` / GATT characteristic registry —
  `0x2A37 = Heart Rate Measurement` (a characteristic UUID, not a
  service).
- Bead gx8b (app repo) — the 2026-08-26 first sighting, the 0xC001
  IMEI-frame circumstantial link, and the n>1 shipping bar.
- NearSight `Sources/Parsers/VZ5GReceiverParser.swift` and
  `research/sweep-2026-10-05-candidates.md`.
