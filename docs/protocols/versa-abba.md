# Versa (ABBAFF00) Plugin

## Overview

An **unidentified** BLE device family advertises with localName exactly `"Versa"` together with the 128-bit custom service UUID `ABBAFF00-E56A-484C-B832-8B17CF6CBFE8` and a short service-data blob keyed under the standard Device Information Service short UUID `0x180A`.

**Vendor identification: UNKNOWN.** Public web search (UUID string, the substring `ABBAFF00`, the combination of `Versa` + UUID, and `ABBA` + bluetooth / wearable / manufacturer) returned no hits for this UUID at the time the parser was written. The `"ABBA"` prefix is hex, not ASCII — it almost certainly was chosen for visual distinctiveness rather than to imply a vendor named "ABBA". The `FF00` segment of the prefix follows the conventional Nordic-style `FFxx` primary-service range that custom firmware uses for proprietary services.

This family is **explicitly distinct** from the Fitbit Versa / Sense / Inspire / Charge / Luxe / Ace product line, which is handled by `FitbitVersaParser`:

| Signal | Fitbit Versa (FitbitVersaParser) | This parser (VersaABBAParser) |
|---|---|---|
| Service UUID | `FD62` (SIG-allocated to Fitbit Inc.) | `ABBAFF00-E56A-484C-B832-8B17CF6CBFE8` (custom 128-bit) |
| Local name | `Versa 2`, `Versa 4`, `Sense`, `Inspire`, `Charge`, `Luxe`, `Ace` (with model number) | `Versa` (bare, no number) |
| 0x180A service data | observed (e.g. `3d0488b101`) | observed (e.g. `2004b12a03`, `2304db5703`) |

The bare `"Versa"` local name and the custom service UUID are the two anchors. Both Fitbit and this unidentified family co-exist in the same residential capture set, so the parsers must not overlap.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Local name | `"Versa"` (exact match required, no model suffix) |
| Service UUIDs | `ABBAFF00-E56A-484C-B832-8B17CF6CBFE8` (case-insensitive; short canonical and 128-bit forms both accepted) |
| Service data key | `0x180A` (Device Information Service — unusual to find in advertising) |
| Address type | Random |
| Manufacturer data | Not observed in any capture |

### 0x180A Service-Data Payload (5 bytes)

```
Captures:
  2004 b1 2a 03
  2304 db 57 03
```

The 5-byte 0x180A payload varies across devices. `0x180A` is the standard GATT Device Information Service UUID; its appearance as **service-data in an advertisement** (rather than GATT-only) is a vendor firmware quirk. Speculative byte interpretations the data is consistent with:

- `20 04 …` / `23 04 …` — possible TLV (`type=0x20` or `0x23`, `length=0x04`, then 4 payload bytes), where the trailing 4 bytes could plausibly encode a device serial / firmware identifier.
- `… 2a 03` / `… 57 03` — could be little-endian 16-bit values (`0x032A`, `0x0357`) but no public correlation has been observed.

Without a controlled capture (vendor app open, device interaction) we cannot decode the payload. The parser surfaces it verbatim as `dis_payload_hex` for forensic inspection and future analysis.

### Stable Key

We use `versa_abba:<macAddress>` because the advertisement carries no device-stable identifier we can recover. MAC rotations on the underlying random BD_ADDR will produce multiple keys until a per-device anchor (e.g. a stable byte position in the 0x180A payload across captures) is identified.

## Detection Significance

- **Unknown device.** Without vendor attribution we cannot say whether this is a wearable, a smart-home device, a vehicle accessory, or something else. It advertises continuously enough to be picked up across multiple sightings, suggesting an always-on or frequently-active device.
- **Distinct from Fitbit Versa.** Surface separately so Fitbit-specific signals (occupancy, wearer presence) are not contaminated.

## What We Cannot Parse from Advertisements

- Vendor / product identity — not derivable from advertising alone.
- The 5-byte 0x180A payload — opaque, no public decoder.
- Per-device stable identifier — none found; we fall back to the MAC address.

## References

- No public references found. Web search (Google, GitHub) for `ABBAFF00-E56A-484C-B832-8B17CF6CBFE8`, `ABBAFF00`, and combinations with `Versa` returned no results as of 2026-05-20.
- For comparison: [Bluetooth SIG Assigned Numbers](https://www.bluetooth.com/specifications/assigned-numbers/) — `0x180A` is the Device Information Service; `FD62` (used by Fitbit, the other "Versa" family) is SIG-assigned to Fitbit Inc.
