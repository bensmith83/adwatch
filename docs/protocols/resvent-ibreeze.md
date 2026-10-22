# Resvent iBreeze CPAP / BPAP ("ResAssist")

## Overview

Resvent iBreeze Auto CPAP / iBreeze BPAP / iBreeze plus / iDisc devices pair
with the **ResAssist** app (`com.resvent.newapp1`, uni-app/DCloud hybrid —
BLE logic in `app-service.js`). Passively the device is identifiable by name
(and, on the WiFi-capable generation, a 16-bit service UUID); the name tail
may carry a serial. No therapy state is broadcast.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | *(none)* | Resvent has no SIG CID; no manufacturer-data parsing. |
| Local name | contains `iBreeze` (case-sensitive) | Primary. Full name validated by `/([0-9]\|[A-Z]){2}[0-9]{6}$/`. |
| Service UUID (16-bit) | `0xA002` (AD bytes `02 A0`) | WiFi-capable "lx" variant only. The app compares against the string `000002A0-…`; see byte-order note. |

### Byte-order note (0x02A0 vs 0xA002)

The app matches `advertisServiceUUIDs[0] == "000002A0-0000-1000-8000-00805F9B34FB"`,
but the WiFi-variant GATT service is `0xA002` (write `C304`, notify `C305`).
The report's hypothesis: the uni-app bridge surfaces the 16-bit UUID in raw
little-endian wire order, so the device really advertises `0xA002`
(wire `02 A0`). Match `0xA002` and also accept a `0x02A0` form.
**Unconfirmed — needs a live capture.**

### Device-name tail

`[A-Z0-9]{2}[0-9]{6}` at the end of the name — a model/serial code. The
6-digit tail is a plausible per-unit serial (unverified).

## What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Vendor/product | name contains `iBreeze` | |
| Candidate serial | 8-char name tail | Treat as PII if confirmed unit-unique |
| Generation | `0xA002`/`0x02A0` present → WiFi-capable "lx"; absent → legacy | Legacy GATT service `1B7E8251-2877-41C3-B46E-CF057C562023` is generally not advertised |

## What Requires GATT Connection

- All therapy data and commands (three GATT profiles; payload crypto
  `EncryptData` in minified JS).
- BLE→WiFi provisioning (Profile B, service `0xA002`) — the app writes
  WiFi SSID/password so the CPAP reaches ResAssist Cloud.

## Identity Hashing

```
identifier = SHA256("resvent:" + name_tail)[:16]   # if tail confirmed stable
identifier = SHA256("resvent:" + mac)[:16]         # otherwise
```

## Detection Significance

- `iBreeze` in the name ⇒ Resvent CPAP user (sleep-apnea inference).
- If the tail is a serial, the name is a persistent identifier independent
  of MAC randomization.
- The service UUID passively distinguishes WiFi-generation units.

> **Naming overlap:** BMC Medical's report also lists "iBreeze" among its
> device class ([bmc-medical-cpap.md](bmc-medical-cpap.md)); BMC units are
> matched by `BMC_*` names, Resvent by `iBreeze`.

## adwatch Status

No plugin. A future plugin would match name substring `iBreeze` OR 16-bit
service `0xA002`, extract the 8-char tail, and tag `variant=lx` when the
service UUID is present.

## References

- apk-ble-hunting `reports/resvent-newapp1_passive.md` (Stage 4: `reports/resvent-newapp1.md`)
- App code cited: `assets/apps/__UNI__FA93E01/www/app-service.js:41` (name match, regex, service-UUID check, GATT profiles), `:8` (device types)
