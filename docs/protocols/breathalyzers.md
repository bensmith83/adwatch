# Personal Breathalyzers (BACtrack, Andatech AlcoSense/AlcoFind, iSober/AlcoScan)

## Overview

Bluetooth breathalyzers are **connection-only** peripherals. On power-on a
unit emits a connectable advertisement so its app can find it; **no BAC value,
test state, battery or sensor reading is ever in an advertisement** — results
arrive only as GATT notifications after connecting. A passive scanner sees
presence + identity: a company ID / vendor service UUID (BACtrack) or a model
name prefix (Andatech, iSober).

Three vendors from apk-ble-hunting batches 26–28:

| Vendor | App | Passive signature |
|--------|-----|-------------------|
| BACtrack (KHN Solutions) — Mobile, C6, C8 | `bactrack_mobile` | CID `0x09A8` and/or vendor service UUIDs |
| Andatech — AlcoSense Nexus/Elite, AlcoFind DA01 | Andalink | name prefix |
| AlcoScan / iSober — AL8800BT, iSober S Pro BLE (ALP-1 is Classic BT) | iSober | name prefix |

## BLE Advertisement Format

### Identification — BACtrack

The app ORs two scan filters (`a/C1547a.java:252,255`); either alone is
sufficient.

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x09A8` (2472), wire `a8 09` | SIG: **KHN Solutions LLC** (BACtrack) — confirmed against adwatch's `_bt_company_ids.py`. App filters `setManufacturerData(2472, new byte[0])` = any payload. |
| Service UUID | `0000FFF0-…` | classic Mobile family (generic 16-bit — weak alone) |
| Service UUID | `0000FFA0-…` | (generic 16-bit — weak alone) |
| Service UUID | `3CAA0001-0060-4787-9DA2-533C53B399A0` | vendor 128-bit |
| Service UUID | `CD06FD00-4AFF-11E3-8F96-0800200C9A66` | vendor 128-bit |
| Service UUID | `D12EFFF0-1243-47A9-952C-F962382D49BB` | vendor 128-bit |
| Service UUID | `E8F90001-0708-430D-93C2-37A17A6191FC`, `E8F90002-…` | vendor 128-bit |
| Service UUID | `A90D0000-4DC3-4E77-9EC2-B0AB30D1E075` | vendor 128-bit |
| Local name | not used | the meta hint `BT-` was **not** found in the app |

Full 128-bit forms are from the companion `bactrack-bactrack_mobile.json`; the
passive report lists them truncated. Each device generation advertises one of
these UUIDs (generation → per-family characteristic set). Notify
characteristics: `0000FFF1` (classic Mobile), `862BFFF1-7D59-4359-8B59-A96DB28BC679`
(C-series).

**Manufacturer-data bytes beyond the CID are undocumented** — the app never
reads them. Do not decode them until a live capture exists.

### Identification — Andatech (Andalink)

Name matched after `.trim().toUpperCase(Locale.ROOT)` (`Helper/BleHelper.java:66,724,771,775`).

| Family | Name prefix | GATT (post-connect) |
|--------|-------------|---------------------|
| AlcoSense (Nexus / Elite; model const `W10`) | `WAT`, `WELL`, `SCRAM`, `OUT`, `DEIMOS`, `HLX` | `fff0` / `fff1` |
| AlcoFind DA01 | `ALCO` | `ffe0` / `da01` (serial on `da04`); auto-pair PIN `000000` |
| DFU mode | exact `AL8800BT-UP` | — |

No service-UUID, manufacturer-data or company-ID filter.

### Identification — iSober / AlcoScan

FastBle `setDeviceName` prefix filter (`defpackage/z92.java:735`); model picked
from `<PREFIX>_<suffix>` by `defpackage/sm0.java`.

| Name prefix | Notes |
|-------------|-------|
| `SENTECH`, `SEN0000`, `SENE148`, `SENE6JZ` | Sentech OEM |
| `AL8800` (e.g. `AL8800BT_xxxx`), `AL8500` | AlcoScan |
| `IBLOW10`, `SBP0001` | |
| `ALP-1` (name contains) | **Classic Bluetooth / SPP** (`00001101`) — not visible to an LE scanner |

> **Cross-vendor overlap.** Andatech's DFU name `AL8800BT-UP` starts with
> iSober's `AL8800` prefix. *Inference (this doc, not stated in either
> report):* both apps likely drive the same AL8800BT-class OEM hardware (both
> talk `fff0`/`fff1`); a passive matcher
> should label `AL8800…` as "AL8800BT breathalyzer" rather than pick a brand.

### What We Can Parse from Advertisements

| Field | Source |
|-------|--------|
| Vendor / device class (alcohol tester) | CID / UUID / name prefix |
| Model family | name prefix (Andatech, iSober); service UUID generation (BACtrack) |
| DFU mode | name `AL8800BT-UP` |
| Presence + MAC | radio |

### What Requires GATT

- BAC result and test state machine (warm-up → blow → analyzing → result):
  BACtrack notify `FFF1`/`862BFFF1`; AlcoSense T-/B-codes on `fff1`; AlcoFind
  opcodes on `da01`; iSober `T11` CSV on `fff1` (field 2 = PASS/FAIL or BAC,
  field 3 = unit).
- Serial numbers (BACtrack DIS `2A25`; AlcoFind `da04`; iSober `B23` response).

None of the three apps implements a pairing gate on the LE path (AlcoFind
auto-pairs with `000000`) — any nearby central can connect and read results.

## Identity Hashing

No payload identifier is broadcast; all reports say address randomization is
a firmware property not visible from the app.

```
identifier = SHA256("breathalyzer:<vendor>:" + mac)[:16]
```

## Detection Significance

- **Sensitive inference from presence alone:** "someone nearby has a
  breathalyzer out / switched on" (the reports call this mildly sensitive).
  Andatech's `SCRAM` prefix may be worth flagging separately (SCRAM is also
  the name of a court-ordered alcohol-monitoring brand — outside knowledge,
  not from the report; the relationship is unverified).
- Short-lived adverts (power-on to test) — low tracking value unless the
  address is static.
- iSober readings are also uploaded to a Firebase RTDB (`isober-3f8f4`) — a
  cloud surface separate from BLE.

## Plugin gaps

No adwatch plugin matches today. A future `breathalyzer` plugin could match:
CID `0x09A8` or the five vendor 128-bit BACtrack UUIDs (not `FFF0`/`FFA0`
alone); names `^(WAT|WELL|SCRAM|OUT|DEIMOS|HLX|ALCO)` (Andatech — `OUT`/`WAT`/
`WELL` are short, generic prefixes and need care against false positives);
`^(SENTECH|SEN0000|SENE148|SENE6JZ|AL8800|AL8500|IBLOW10|SBP0001)`
(iSober/AlcoScan). Presence only — no decode.

## References

- apk-ble-hunting `reports/bactrack-bactrack_mobile_passive.md` (`a/C1547a.java:252,255`; UUID registry `g/c.java`) and `bactrack-bactrack_mobile.json` (full UUIDs)
- apk-ble-hunting `reports/andatech-andalink_passive.md` (`Helper/BleHelper.java:42,66,102,713,724,771,775`; `Model/BLEProtocol.java:51`)
- apk-ble-hunting `reports/breathalysers-isober_passive.md` (`defpackage/z92.java:700,735`; `defpackage/sm0.java`)
- adwatch `src/adwatch/_bt_company_ids.py` (`0x09A8: KHN Solutions LLC`)
