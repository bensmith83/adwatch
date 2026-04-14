# KS03 Generic BLE HID Remote

## Overview

"KS03" is the factory name stamped on a large family of unbranded Chinese BLE
HID peripherals. Physically they appear as key-fob shutters, finger rings,
selfie remotes, phone-page turners, TikTok scrollers, or cheap e-reader
clickers. All of them emulate a BLE HID keyboard and typically send a
`Volume-Up` keycode, which on iOS / Android triggers the camera shutter or a
page change in reading apps.

These devices are whitelabeled by hundreds of Amazon / AliExpress / Temu
sellers under different brand names, but the BLE advertisement fingerprint is
consistent across all of them, so adwatch identifies them generically.

## BLE Advertisement Fingerprint

### Identification

| Field | Value | Notes |
|-------|-------|-------|
| Local Name | `KS03~XXXXXX` | `XXXXXX` = low 3 bytes of the device MAC, lowercase hex |
| Service UUIDs | `0x1812`, `0x180F` | HID over GATT + Battery Service |
| AD Type | `0xFF` (Manufacturer Specific Data) | Contains a placeholder payload |

Example names observed:

- `KS03~2520e0`
- `KS03~98dad0`

### Manufacturer Data

```
f0 01 02 03 04 05 06 00
^^^^^                 — claimed company ID 0x01F0 (Mobvoi)
      ^^^^^^^^^^^^^^ — payload
```

The claimed company ID `0x01F0` resolves to *Mobvoi Information Technology*
in the Bluetooth SIG registry, but **these devices are not Mobvoi products**.
The byte sequence `02 03 04 05 06 00` is the canonical **uninitialized
Telink / Beken reference-SDK template** — the factory shipped reference
firmware in which the `adv_data[]` array was never filled in with real vendor
data. The same sequential-byte payload shows up in many Telink TLSR825x-based
unbranded gadgets.

Practical consequences:

- The company ID is **not trustworthy** for attribution.
- The manufacturer data carries **no device-specific information** (no serial,
  no battery %, no button state).
- The only reliable identifying field is the local name.

## Parsing

adwatch matches via `local_name_pattern=r"^KS03~[0-9a-fA-F]{6}$"` and emits:

| Field | Value |
|-------|-------|
| `parser_name` | `ks03_hid_remote` |
| `beacon_type` | `ks03_hid_remote` |
| `device_class` | `remote` |
| `metadata.mac_suffix` | low 3 bytes from the name |
| `metadata.mfg_placeholder` | `True` when mfg data matches the SDK template |
| `metadata.claimed_company_id` | `0x01F0` (only set when placeholder detected) |
| `metadata.advertises_hid` | `True` if service UUID `0x1812` is advertised |

## Detection Density

In the adwatch export from 2026-04-13, two distinct KS03 devices were seen in
the last 8-hour window (MAC suffixes `2520e0` and `98dad0`). Typical
home environments show 0–3 of these at any time. In dense urban or retail
environments (cafes, malls) sightings cluster into the dozens, since the same
product is sold under hundreds of brands.

## References

- [Apple Community thread: Unknown Bluetooth device named KS03](https://discussions.apple.com/thread/254258540)
- [9meters: What Is This Unknown Bluetooth Device Named KS03?](https://9meters.com/technology/networking/unknown-bluetooth-device-named-ks03)
- [Bluetooth SIG assigned numbers](https://www.bluetooth.com/specifications/assigned-numbers/) (company ID 0x01F0 = Mobvoi)
- [Telink TLSR825x BLE SDK](https://wiki.telink-semi.cn/) — see `adv_data[]` default in the reference examples

## Privacy Note

Because every KS03 unit broadcasts its MAC-suffix in cleartext and the MAC is
**not randomized**, these devices are trivial long-term trackers of their
owner. Carrying one in a pocket exposes a stable public identifier to every
scanner in range.
