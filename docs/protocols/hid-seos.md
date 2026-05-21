# HID Global Seos / Mobile Access Plugin

## Overview

**HID Global** is the dominant vendor in commercial physical access control — door readers, parking-gate readers, elevator-access readers, secure printer-release stations, and time-and-attendance terminals across enterprise campuses, hospitals, universities, hotels, and government facilities.

**Seos** is HID Global's cryptographic identity-credential framework. It is the foundation of HID **Mobile Access**: a phone (running the HID Mobile Access app for iOS / Android, or storing the credential in Apple Wallet) provisions a Seos credential, and an HID **Mobile Access reader** — typically the [Signo](https://www.hidglobal.com/products/readers/signo/40) line or the older iCLASS SE / multiCLASS SE — verifies it over BLE or NFC when the phone is presented.

Seos supports many applications beyond physical access (cashless vending, secure printing, network login, time-and-attendance), but the BLE advertisement shape we surface here is overwhelmingly access-control infrastructure.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Local name | `Seos` (exact, case-sensitive, no suffix) |
| Manufacturer data | absent |
| Service UUIDs | absent |
| Service data | absent |

HID Global has not publicly disclosed a 16-bit Bluetooth SIG service UUID for Mobile Access. The phone-side bare advertisement emitted by the HID Mobile Access app contains nothing but the GAP local name `"Seos"`; reader-side advertising payloads are likewise bare (richer payloads may appear in the scan response, which CoreBluetooth folds into `localName` / `serviceData` after a discovery, but the *advertising* PDU itself is empty beyond the name).

### Disjointness Rule

The string "Seos" is also a Greek female name and the name of unrelated IoT modules and projects. To avoid over-attribution we require the advertisement to be **completely bare**: any manufacturer data, service UUID, or service data alongside a `Seos` local name disqualifies the match.

Concretely:

- `localName == "Seos"` exactly (case-sensitive — HID's app emits `Seos`, not `SEOS` / `seos`).
- AND `manufacturerData == nil`.
- AND `serviceUUIDs.isEmpty`.
- AND `serviceData.isEmpty`.

If a future research export shows the Mobile Access app advertising a stable 128-bit service UUID, the matcher can be relaxed to accept that signal as an additional disjunct.

### Stable Key

We do **not** set a stable key. The local name `"Seos"` is identical across every emitter (phone or reader), so it carries no per-device entropy, and the MAC address is randomized on iOS. Downstream consumers that want to count "Seos" sightings can group by `parserName`.

## Examples

| Capture | Inference |
|---|---|
| `localName="Seos"`, no mfr / svc / svc-data | `device_class=access_control`, `vendor=HID Global` |
| `localName="Seos"`, has manufacturer data | nil — unrelated device that shares the name |
| `localName="Seos Reader"` | nil — not an exact match |
| `localName="seos"` / `"SEOS"` | nil — HID's app emits exactly `Seos` |

## References

- [HID Mobile Access overview](https://www.hidglobal.com/solutions/mobile-access-solutions)
- [HID Seos credential platform](https://www.hidglobal.com/product-mix/seos)
- [HID Mobile Access iOS app](https://apps.apple.com/us/app/hid-mobile-access/id843238107)
- [HID Mobile Access FAQ (PDF)](https://doc.origo.hidglobal.com/faq/portal/HID_Mobile_Access_FAQ.pdf)
- [HID Signo Reader 40](https://www.hidglobal.com/products/readers/signo/40)
- `research/adwatch_export 8.json` — 2026-05-20 bare `"Seos"` sighting (1 emitter)
