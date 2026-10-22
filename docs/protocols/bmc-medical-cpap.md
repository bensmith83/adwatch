# BMC Medical CPAP / APAP ("PAP Link")

## Overview

BMC Medical (China) makes CPAP/APAP machines sold as G2/G3, RESmart and
iBreeze-branded units (families M1/M1A, E5, P5, S1/SK, P1/PK, plus a
`Hi-A-12E0K` placeholder-named variant). The companion app is **PAP Link**
(`com.bmc.paplink`).

The device is **connection-oriented, not a beacon**. The advertisement
carries only identity (device-name prefix, or for one family an ASCII
model/serial string embedded in the raw advert) plus a 2-byte
protocol-generation flag in manufacturer data. All therapy data (pressure,
AHI, usage) flows over **encrypted GATT** after connect (AES/3DES/RSA in
`libnative-lib.so`). Passive richness: **LOW**.

> **Naming overlap:** the report lists "iBreeze" among BMC's device class.
> adwatch also documents the Resvent iBreeze line
> ([resvent-ibreeze.md](resvent-ibreeze.md)), which is discovered by an
> `iBreeze` name substring — BMC adverts are matched by the `BMC_*` prefixes
> below, not by `iBreeze`.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | *(none)* | BMC Medical has no SIG company ID. The `0xFF` AD starts with `AA 02`, which is a magic, **not** a CID (would read as `0x02AA` if mis-parsed as one). |
| Service UUID | *(none advertised)* | GATT service discovered dynamically after connect. |
| Local name prefixes | `BMC_M1A`, `M1A`, `BMC_M1` | Mini family |
| | `BMC_E5`, `E5`, `BMC_P5`, `P5` | New-protocol family |
| | `BMC_S1`, `BMC_SK` | SO1 family |
| | `BMC_P1`, `BMC_PK` | P1/PK family |
| | `Hi-A-12E0K` | Placeholder; real name is embedded in the raw advert (below) |

The app scans with **no ScanFilter** (LOW_LATENCY, AGGRESSIVE match) and
does all matching in `onScanResult`. The short prefixes `E5`, `P5`, `M1A`
are weak on their own — prefer the `BMC_` forms or require additional
context before claiming a match.

### Manufacturer-Specific AD (type `0xFF`)

| Offset (in AD payload) | Field | Size | Decode |
|---|---|---|---|
| 0 | Magic | 1 | `0xAA` |
| 1 | Protocol generation | 1 | `0x02` → "new protocol" (E5/P5) |
| 2… | Opaque | var | Not parsed in Java; any decode lives in `libnative-lib.so` (unresolved) |

`AA 02` present ⇒ `isNewProtocol = true` (selects new native framing). It
is a boolean generation flag, not telemetry.

### Embedded model/serial string (`Hi-A-12E0K` family)

For devices whose GAP name is `Hi-A-12E0K`, the app decodes the **whole raw
scan record as UTF-8** and searches it:

- contains `BMC_` → name = the 15 chars starting at `BMC_`
- else find `M1A` → name = `"BMC_" +` the 11 chars starting at `M1A`

So the real model/serial is broadcast as ASCII somewhere in the advertising
payload (the AD structure that carries it is not stated by the report).

## What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Vendor = BMC Medical | name prefix | |
| Family (Mini / NewPro / SO1 / P1) | name prefix | |
| Model/serial string | GAP name, or ASCII substring for `Hi-A-12E0K` | Whether the 11-char tail is per-unit is **unverified** |
| Old vs new protocol | `0xFF` AD begins `AA 02` | |

## What Requires GATT Connection

- All therapy/usage telemetry and commands. Notify/write chars per family:
  Mini `FFF1/FFF2`, SO1 `FE62/FE61`, NewPro (E5/P5) `FE64`.
- Native framing (start marker `0xA55A`, token/param/length) and
  AES/3DES/RSA key exchange.

## Identity Hashing

If the embedded `BMC_…` string proves unit-unique on a live capture:

```
identifier = SHA256("bmc_cpap:" + model_serial_string)[:16]
```

Otherwise fall back to `SHA256("bmc_cpap:" + mac)[:16]`. Address type
(public vs random) is not determinable from the app.

## Detection Significance

- Any `BMC_*` advert discloses "this person uses a CPAP" → sleep-apnea
  inference (medical, sensitive). Device-class disclosure is **certain**.
- The "unique per-unit tracking" claim is **downgraded / unverified** by the
  report's Stage 5b audit: the 11 trailing chars may be a per-unit serial or
  just a model/variant code.

## adwatch Status

No plugin. A future plugin would match the `BMC_*` / `Hi-A-12E0K` name
prefixes, scan raw advert bytes for the ASCII `BMC_`/`M1A` substring, and
flag `AA 02` at the start of the `0xFF` AD as `protocol=new`.

## References

- apk-ble-hunting `reports/bmc-paplink_passive.md` (Stage 4b; GATT catalog in `reports/bmc-paplink.md`)
- App code cited by the report: `BluetoothManagerProxy.java:135-147` (Hi-A name reconstruction), `:615`/`:644` (unfiltered scan + settings), `:667-680` (`parseAdvertisingData`, `AA 02` check); `BluetoothConnector.initServiceAndChara` `:492-505`
