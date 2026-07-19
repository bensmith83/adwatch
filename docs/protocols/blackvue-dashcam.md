# BlackVue Dashcam (Pittasoft DR-series)

## Overview

BlackVue is the consumer car-dashcam line from **Pittasoft Co., Ltd.**
(Seoul, Korea). The DR-series — DR750X, DR770X, DR900X, DR970X, plus
"Box", "Box Plus", and "Box Pro" trims — exposes Bluetooth alongside
Wi-Fi for the "Seamless Pairing" flow used by the BlackVue smartphone
app. In idle / discovery state, the dashcam advertises a **name-only**
BLE frame: no manufacturer data, no service UUIDs, no service data.
GATT services are only exposed post-pair.

## Supported Models

Any DR-series dashcam advertising a localName matching the regex
`^BlackVue[0-9]{3,4}X?(?:Box|Plus|Pro)?P?-[0-9A-F]{6}$`. Captured in
the wild as `BlackVue770XBoxP-EE10A2` (DR770X Box Plus/Pro).

The parser does not attempt to distinguish Plus vs Pro from the `P`
token alone — Pittasoft does not publish the exact mapping in any
public manual we could find.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Local name | `BlackVue<MODEL><VARIANT?>-<MAC6>` | name-only ad; see template below |
| Manufacturer data | *(none)* | Pittasoft does not emit mfg data in the discovery frame |
| Service UUIDs | *(none in ad)* | GATT services exposed only after pairing |
| Address type | `random` | BD_ADDR rotates per the BT 4.2 stack default |

Template parts:

- `<MODEL>` — 3-4 model digits, optionally followed by `X` (e.g. `770X`,
  `900X`, `750X`, `970X`). The parser prepends `DR` to produce the
  canonical product name (`DR770X`).
- `<VARIANT?>` — optional trim token: `Box`, `BoxP` (Box Plus/Pro),
  `Plus`, `Pro`. Absent on the entry-tier SKUs.
- `<MAC6>` — exactly 6 uppercase hex chars; the last 3 BD_ADDR bytes
  printed on the device's connectivity label and reused as the
  dashcam's Wi-Fi SSID suffix.

### What We Can Parse

| Field | Source | Notes |
|-------|--------|-------|
| Vendor | hard-coded | `Pittasoft` |
| Product | derived from MODEL | e.g. `BlackVue DR770X` |
| `model` | localName | `DR<MODEL>` |
| `variant` | localName | optional; `Box` / `BoxP` / `Plus` / `Pro` |
| `mac6` | localName | last 3 BD_ADDR bytes, uppercase hex |

### What We Cannot Parse from the Advertisement

- Recording state (parked / driving / event triggered).
- Storage usage, microSD health.
- Firmware version.
- GPS lock state, Wi-Fi connectivity to BlackVue Cloud.
- Live video stream (Wi-Fi only).

All live state lives behind the dashcam's HTTP API on
`10.99.77.1:80` (Wi-Fi side) — see community projects such as
`hackvue` and `bartbroere/blackvue-wifi`. The BLE advertisement only
proves a BlackVue is in range and which model/SKU it is.

## Stable Identity

`<MAC6>` is the stable per-unit identifier — printed on the device,
persists across firmware updates, and survives the rotating BD_ADDR
that the random-address advertising scheme uses:

```
stable_key = blackvue:<MODEL>:<MAC6>
identifier = SHA256(stable_key)[:16]
```

## Detection Significance

- A vehicle with an in-cabin BlackVue is in range (parked or driving).
- Box / Box Plus / Box Pro trims target commercial fleet operators,
  while plain DR-series is more common in personal vehicles.
- Pittasoft dashcams continue advertising even when the vehicle is
  parked (parking mode uses motion-triggered low-power recording), so
  long-dwell sightings indicate parked vehicles rather than transient
  drive-bys.

## References

- [BlackVue DR770X Box manual — Bluetooth pairing](https://manual.blackvue.com/docs/dr770x-box/playing-and-managing-videos/using-your-smartphone-android-ios-dr770x-box-series/)
- [BlackVue DR770X Box product specs (Bluetooth 2.1+EDR/4.2)](https://manual.blackvue.com/docs/dr770x-box/product-specifications/product-specifications-dr770x-box-series/)
- [BlackVue DR770X Box Pro product specs](https://manual.blackvue.com/docs/dr770x-box-pro/product-specifications/product-specifications-dr770x-box-pro-series/)
- [BlackVue Seamless Pairing firmware notes (DR900X / DR750X / DR750-2CH LTE)](https://blackvue.com/firmware-updates-seamless-pairing-for-dr900x-dr750x-and-dr750-2ch-lte/)
- [BlackVue SSID `<MODEL>-<MAC6>` convention](https://helpcenter.blackvue.com/hc/en-us/articles/12059688449305-What-is-the-camera-s-WiFi-SSID-and-password)
- Community Wi-Fi reverse-engineering (no BLE coverage, but vendor context): [hackvue](https://github.com/Digital-Nebula/hackvue), [blackvue-wifi](https://github.com/bartbroere/blackvue-wifi)
