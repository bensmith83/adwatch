# Haier / Candy / Hoover "hOn" Plugin

## Overview

The **hOn** ecosystem ([hon-smarthome.com](https://hon-smarthome.com/)) is the unified IoT-control app for the Haier group's white-goods brands — **Haier**, **Candy**, and **Hoover** (the latter two acquired by Haier in 2019). Connected washing machines, dryers, dishwashers, refrigerators, ovens, and air conditioners across all three brands surface in a single app under one account.

When a hOn appliance is in **wifi-credential-provisioning mode** — i.e. recently power-cycled or factory-reset and waiting for the hOn app to push it SSID / password — it advertises continuously over BLE behind GATT service UUID `0xFF09` (the hOn pairing service) plus a manufacturer-data payload behind the SIG-reserved pseudo company ID `0xFFFF`. Haier-Candy never registered a real CID for this advertisement path, presumably because the BLE channel is only used for one-shot provisioning and never for steady-state telemetry (that runs WiFi → Haier cloud → hOn app).

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Pseudo company ID | `0xFFFF` (SIG "test / invalid" — **not** assigned to Haier) |
| Service UUIDs | `0xFF09` (hOn provisioning service) — **required** for gating |
| Fixed signature | First 4 payload bytes `02 7c e9 13` — **required** for gating |
| Local name | `<brand_prefix><model_code><serial>` ASCII string (always present) |

Because `0xFFFF` is reused by countless chinese-OEM gadgets in the "I didn't pay SIG for a CID" tier, we gate on **both** the `02 7c e9 13` signature **and** the `FF09` service UUID before accepting an advertisement.

### Manufacturer Data Layout (17 bytes)

```
Bytes 0..1   : ff ff                       ← LE pseudo company ID 0xFFFF
Bytes 2..5   : 02 7c e9 13                 ← fixed hOn protocol signature
Bytes 6..8   : 3-byte per-unit token       ← varies per advert; surfaces as
                                              `per_unit_token`. Likely a
                                              firmware-side nonce or a
                                              hash of the device serial —
                                              not yet confirmed.
Bytes 9..10  : 02 b4                       ← TLV magic for the model-code field
Byte  11     : LL                          ← length of model-code content
Bytes 12..   : LL ASCII bytes (NUL-padded
               when LL < natural width)    ← ASCII model code; we strip
                                              trailing NULs and surface as
                                              `model_code`. We always
                                              expose `model_code_hex` for
                                              the raw bytes regardless.
```

Observed across the 3 captures:

| Local name | Token | LL | Model bytes | Decoded |
|---|---|---|---|---|
| `ASHDJW61F37100131` | `41 35 70` | 05 | `44 4a 57 36 04` | `DJW6` (with `\x04` trailer) |
| `AQLDJW61G03300208` | `8d 5b c2` | 05 | `44 4a 57 36 04` | `DJW6` (with `\x04` trailer) |
| `AFYDL570G04401374` | `92 cb 9c` | 04 | `35 59 55 00`    | `5YU` (NUL-padded) |

Note that the LL byte does not perfectly bracket the printable ASCII content — for LL=5 captures, the last byte (`0x04`) is non-printable, suggesting the field is actually 4 ASCII chars + 1 byte trailer or that 0x04 is part of the model identifier encoded as a numeric. Our parser surfaces both the ASCII-decoded `model_code` (when the trimmed bytes are entirely alphanumeric) and the raw `model_code_hex` for honest reproducibility — analysts can resolve the ambiguity once more samples arrive.

### Local Name Format

`<brand_prefix><model_code><serial>`:

| Prefix | Brand / line |
|---|---|
| `AQL` | Candy **Aquasensitive** washing machines |
| `ASH` | Hoover/Candy washing-machine series |
| `AFY` | Haier dryer / washing-machine variant (likely a Candy line) |

We surface the 3-character prefix as `brand_prefix` to enable simple per-line counting.

### Stable Key

`haier_hon:<localName>` — the local name carries the device serial number in plaintext, so collisions across MAC rotations collapse cleanly.

## Detection Significance

- **Laundry / kitchen indicator.** A hOn-format advert during a scan means there is at least one Haier-group major appliance in or near the dwelling, in pairing mode.
- **Pairing-mode-only signal.** Continuous `FF09 + 02 7c e9 13` adverts mean a washer/dryer/dishwasher has been reset or has lost its WiFi credentials and is sitting unprovisioned — possibly an indicator of recent power loss, recent firmware update, or a user mid-setup. Once the unit is paired it stops advertising on BLE.
- **Cross-brand grouping.** Because Candy / Hoover are sub-brands of Haier post-2019, multiple `brand_prefix` values may represent appliances from the same household.

## What We Cannot Parse from Advertisements

- **Live wash / dry cycle status.** Cycle, remaining time, temperature, spin speed, error codes, water usage — all carried via the hOn cloud API over WiFi, never advertised on BLE.
- **Drum load / weight sensors.** Same — cloud only.
- **Device serial cryptographic identity.** The 3-byte token may be a rotating nonce or a serial hash; we surface it but cannot yet correlate to a stable identity beyond what the local name already gives us.

## References

- [hOn smart-home portal](https://hon-smarthome.com/) — official Haier/Candy/Hoover landing page.
- [Andre0512/hon](https://github.com/Andre0512/hon) — Home Assistant integration; cloud-API decoder.
- [gvigroux/hon](https://github.com/gvigroux/hon) — earlier reverse-engineering effort with full appliance taxonomy.
- [Bluetooth SIG company identifiers](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml) — confirms `0xFFFF` is the reserved "test / invalid" sentinel, not assigned to Haier.
- [pyhOn](https://github.com/Andre0512/pyhOn) — Python cloud-API library used by the HA integration.
