# Anker soundcore audio device

## Overview

**soundcore** is Anker Innovations' audio sub-brand (earbuds, speakers).
A soundcore unit observed in the wild advertises a manufacturer-data payload
that **literally spells the brand name in ASCII**, behind a forged
company-ID prefix — making it a self-identifying, low-false-positive
fingerprint.

This is an **identification-only** parser: there is no public spec for the
soundcore advertising payload and only a single device/session has been
observed, so battery/model/state are deliberately not decoded.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|---|---|---|
| Manufacturer data | contains ASCII `73 6f 75 6e 64 63` = "soundc" | self-identifying anchor (the gate) |
| Company ID | `0x9DF4` (bytes `f4 9d`, LE) | **forged** — not SIG-assigned |
| Service UUID | `DAF59201` (32-bit) | RCSP-family corroborator |
| Address type | `random` | rotating; matches documented soundcore behaviour |

**The ASCII run is the gate** — the device literally names itself. The
parser is registered on both the forged company ID and the 32-bit service
UUID (so it is invoked) and then requires the `"soundc"` ASCII to be present.

### Company-ID caveat

`f4 9d` (LE `0x9DF4`) is **not** a registered Bluetooth SIG company ID —
Anker's real CID is `0x0CC2`. `0x9DF4` is a forged/placeholder prefix typical
of cheap-OEM firmware. It is surfaced honestly in metadata
(`sig_id_status = non_sig_forged`), **not** treated as the attribution.

### Service-UUID corroboration

The 32-bit UUID `DAF59201` shares the `f5da` byte sequence with the
documented soundcore **RCSP** service UUID family (`020cf5da-…`,
reverse-engineered in `andrewseago/d3200-ble-note-downloader`), and that
project notes soundcore devices use **rotating BLE addresses** and recommends
matching on the RCSP service UUID rather than a fixed MAC — both consistent
with our capture (`addressType = random`).

### Byte map (14-byte truncated capture)

```
offset 0–1   f4 9d           forged company ID 0x9DF4 (LE), non-SIG, stable
offset 2–5   8a 8d 22 3f     opaque device/model id field (stable in session)
offset 6–7   00 00           reserved / padding
offset 8..   73 6f 75 6e 64 63   ASCII "soundc…" (start of "soundcore", TRUNCATED)
```

With a single device and one ~3-minute session, every byte is constant in
our data; we cannot yet distinguish a per-device id from a model code in
bytes 2–5.

### What we can surface

| Field | Source | Notes |
|---|---|---|
| `vendor` | ASCII anchor | `Anker (soundcore)` |
| `product` | hard-coded | `soundcore audio device` |
| `brand_string` | mfg bytes 8.. | decoded printable ASCII (`soundc`) |
| `device_id_hex` | mfg bytes 2–5 | opaque stable identity |
| `service_uuid` | serviceUUIDs | `daf59201` when present |
| `company_id` / `sig_id_status` | mfg bytes 0–1 | `0x9df4` flagged forged |

### What we cannot surface

- Battery, exact model, ANC/state — no public advertising-format spec, and a
  single sample. The control protocol (RCSP) is GATT/RFCOMM-only.

## Parser scope (passive only)

Brand identification only. Do **not** read decoded telemetry from this
parser; collect more soundcore sightings (multiple models/units) before
attempting any field decode.

## Stable identity

```
stable_key = soundcore:<device_id_hex>   (mfg bytes 2–5)
identifier = SHA256(stable_key)[:16]
```

Honest given N=1: the 4 id bytes are stable within the observed session;
whether they are per-unit or per-model is unconfirmed.

## Detection significance

- Consumer audio presence; the self-identifying ASCII makes attribution
  rock-solid despite the forged company ID and rotating address.

## References

- [`andrewseago/d3200-ble-note-downloader`](https://github.com/andrewseago/d3200-ble-note-downloader) — soundcore RCSP service UUID (`020cf5da-…`), rotating-address note
- [soundcore RE projects (OpenSCQ30, SoundcoreManager)](https://github.com/topics/soundcore)
- [Bluetooth SIG assigned numbers](https://www.bluetooth.com/specifications/assigned-numbers/) — Anker = `0x0CC2`; `0x9DF4` unassigned
- Captures: `research/nearsight_export 7.json` (1 device, 91 sightings).
