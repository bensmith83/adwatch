# Aftermarket BLE TPMS (Chaoyue/LEEPEE, AiCare/Pingwang, Sysgration, TireMinder)

## Overview

Cheap aftermarket tire-pressure kits (valve-cap or in-wheel sensors, one per
tire, read by a phone app or a small dashboard display) are some of the
loudest connectionless BLE advertisers: each sensor beacons pressure,
temperature, battery and alarm state in the clear, ~24×7 or whenever the wheel
moves, with **no pairing, no encryption and a non-rotating per-tire ID**.

This doc collects four distinct OEM families recovered from apk-ble-hunting
passive reports (batch 26–28). They are **not byte-compatible with each
other** — each needs its own gate and decode:

| Family | Apps (package) | Discovery key | Telemetry carrier | Passive yield |
|--------|----------------|---------------|-------------------|---------------|
| **A. Chaoyue / LEEPEE** (Tymate, many Amazon kits) | `com.chaoyue.acartpms` "TPMS Plus", `com.chaoyue.tyed` "TPMSII" | name contains `TPMS` + mfr-data CID bytes `00 01` | manufacturer data, Java-decoded | HIGH |
| **B. AiCare / Pingwang / elinkthings** (ZEEPIN, Tymate, Jansite) | `aicare.net.cn.itpms` "Smart TPMS" | service UUID `0xFBB0` or `0xFBC0` + mfr data ≥ 11 B | manufacturer data, native-decoded (`libtpms-lib.so`) | HIGH |
| **C. Sysgration** ("Multi Wheel BLE TPMS") | `com.sysgration.tpms.app` | iBeacon with proximity UUID `b54adc00-67f9-11d9-9669-0800200c9a6{6,7,a}` | iBeacon major/minor | HIGH |
| **D. TireMinder** (Minder Research, RV/trailer) | `com.minderresearch.tiremindertpms` | name `TM-Blue22` (+ Nordic UART UUID) | none — 433 MHz sensors, GATT relay | presence only |

> **Do not cross-apply offsets.** All four reports say so explicitly; in
> particular the Chaoyue `0x0001`-style family and the AiCare FBB0/FBC0 family
> are different OEMs even though some brand names (Tymate) appear against both.

### Relationship to existing adwatch plugins

- `src/adwatch/plugins/tpms.py` (v1.1.0) registers on **company ID `0x0001`**
  or local name `^(TPMS|BR)` and decodes `payload[0]`=sensor index,
  `payload[1]×0.02` V battery, `payload[2]−40` °C, `LE16(payload[3..4])/100`
  kPa. **None of the four families below match that layout.** See
  [Plugin gaps](#plugin-gaps) — family A in particular will be *caught by the
  name pattern and mis-decoded*.
- `src/adwatch/plugins/fobo_tpms.py` covers FOBO (Salutica, CID `0x0127`) —
  unrelated to these families.
- [revvo-tire-sensor.md](revvo-tire-sensor.md) covers Revvo fleet in-tire
  sensors (CID `0x086C`) — unrelated.

---

## Family A — Chaoyue / LEEPEE (`com.chaoyue.acartpms`, `com.chaoyue.tyed`)

Both apps (same developer) parse the **same advert family**; acartpms exposes
the full Java decode that tyed partly deferred, and tyed's `getPress`/`getTemp`
confirm the scaling. Both apps index **absolute byte offsets into the whole
scan record** (`getScanRecord().getBytes()` hex-dumped and sliced), not offsets
inside the manufacturer AD.

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Local name | contains `TPMS` | discovery token. tyed excludes names containing `TPMSR_` (a repeater/relay variant, not a tire sensor). |
| "Company-ID marker" | scan-record bytes 9–10 == `00 01` (hex string `"0001"`) | **see endianness note below** |
| No-data sentinel | scan-record byte 26 == `ff` → frame dropped | sensor has no fresh data |
| Frame marker (tyed only) | scan-record byte 7 == `0x13` | "standard data frame" |
| Service UUIDs / service data | none used | acartpms's scanner library is configured with `0xFBB0` but it is not used as a match key |

> **CID endianness — report vs wire.** Both reports call this "company ID
> `0x0001`" because the app string-compares the hex dump of bytes 9–10 against
> `"0001"`. Those are **wire-order** bytes `00 01`; BLE company IDs are
> little-endian, so a stack (bleak, adwatch) reports this as **CID `0x0100`**
> (SIG-assigned to TomTom International BV — a misattribution trap for naive
> CID lookups), **not** `0x0001`. *Inferred (this doc, not stated in the
> reports):* byte 7 = `0x13` is the manufacturer AD's length byte (19 = 1 type
> + 18 value bytes), byte 8 = AD type `0xFF`, and the 18-byte manufacturer
> value is `00 01 | 3 B | sensor ID 3 B | pressure 4 B | temp 4 B | batt | status`.
> This matches the widely-seen generic "TPMS1_xxxxxx" valve-cap sensor family
> but has not been checked against a live adwatch capture.

### Byte layout

Absolute scan-record offsets as the app uses them, plus the equivalent offset
inside the manufacturer-data value (CID included) under the framing inference
above.

| Scan-record offset | Mfr-value offset (inferred) | Field | Size | Decode |
|--------------------|-----------------------------|-------|------|--------|
| 7 | — | AD length (tyed: frame-type marker `0x13`) | 1 | gate (tyed only) |
| 9–10 | 0–1 | CID bytes `00 01` | 2 | gate |
| 11–13 | 2–4 | not read by either app | 3 | — |
| 14–16 | 5–7 | **Sensor ID** | 3 | raw bytes as transmitted, uppercased hex; persistent per tire |
| 17–20 | 8–11 | **Pressure** | uint32 LE | `kPa = raw / 1000` (tyed: `bar = raw / 100000`; raw ≈ Pa) |
| 21–24 | 12–15 | **Temperature** | uint32 LE | `°C = raw / 100` |
| 25 | 16 | **Battery level** | uint8 | raw level; app compares to user low threshold |
| 26 | 17 | **Status / leak** | uint8 | `00` OK, `01` leak / rapid decompression (acartpms latches alarm after 4 consecutive leak frames), `ff` no data (skip) |

Frame is rejected by acartpms if the record is ≤ 56 hex chars.

### Name encoding (tyed only)

tyed parses `name.substring(6,12)` as a 24-bit hex value for **wheel-slot
assignment**: high byte `0x30` / `0x40` = tire 3 / tire 4, low 16 bits in a
fixed `0x04E3..0x09C4` window. App-internal; not needed to decode telemetry.

---

## Family B — AiCare / Pingwang / elinkthings (`aicare.net.cn.itpms`)

BLE library `com.pingwang.tpmslibrary`; raw manufacturer bytes are handed to a
native parser (`libtpms-lib.so`, export `Java_com_pingwang_tpmslibrary_TpmsScan_parse`).
The report's Stage 6a recovered the byte offsets from the unstripped arm64 lib
(DWARF line info) — **resolved, HIGH confidence**.

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `0xFBB0` (`0000FBB0-0000-1000-8000-00805F9B34FB`) | sensor family #1 (`ScanFilter`) |
| Service UUID | `0xFBC0` | sensor family #2 |
| Manufacturer data | present, **≥ 11 bytes** including the CID field | legacy-callback gate (`TpmsScan.java:79-82`) |
| Company ID | **not checked** by the app | the CID field is actually the frame header — see below |
| Local name | passed through, not a match key | |

> **The "company ID" is a frame header.** The native parser sees
> `[CID_LSB, CID_MSB, ...value]` and treats `byte[0]` as a family header
> (`0xAC`, `0xAD`, `0x55`; `0xA0–0xAF` accepted) and `byte[1]` as a subtype.
> So on the wire a stack reports these as CID `0x00AC` (wire `ac 00`, SIG:
> Green Throttle Games) or `0x01AD` (wire `ad 01`, SIG: FlightSafety
> International) — **misattribution traps**; the real discriminator is the
> FBB0/FBC0 service UUID.

### Byte layout (`0xAC` / `0x55` header family)

Offsets into the full manufacturer value **including** the 2 CID bytes
(= what follows `len, 0xFF` in the AD).

| Offset | Field | Size | Decode |
|--------|-------|------|--------|
| 0 | Frame header (= CID LSB) | 1 | `0xAC` (also `0xAD`, `0x55`) — selects family |
| 1 | Subtype (= CID MSB) | 1 | `0x00` for 0xAC family; `0x01` for 0xAD; selects pressure scaling |
| 2 | **Battery** | 1 | `V = b2 × 0.01 + 1.22` |
| 3 | **Pressure** | 1 | `b3 × 3.38 − 30.3` on the XOR-checksum ("mode2") path, else `b3 × 3.144`; subtype `0x15`: `b3 × 5.5`; clamped ≥ 0. Unit per parser constant `pressureUnit = 3` (unit mapping not given in the report) |
| 4 | **Temperature** | 1 | `°C = b4 − 55` |
| 5 | **Status** | 1 | signed int8; alarm / leak / state flags (bit meanings not given) |
| 6 | **MCU version** | 1 | `b6 / 10.0` |
| 7 | **Checksum** | 1 | `(Σ b[2..6]) & 0xFF` **or** `b2^b3^b4^b5^b6` (XOR / "mode2"); validated before decode |
| 8 | **Firmware year + month** | 1 | `year = (b8 >> 4) + 2015`, `month = b8 & 0x0F` |
| 9 | **Firmware day** | 1 | `b9` |
| 10 | **BLE version** | 1 | `b10 / 10.0` |

### `0xAD` header family differences

| Field | 0xAD decode |
|-------|-------------|
| Battery | `b2 × 0.1` |
| Pressure | 16-bit `(b3 << 8) \| b4`, clamp ≥ `0x92`, `p = (adc − 0x92) / 10.0`; `pressureUnit = 2` |
| Temperature | at `b5` (−55) |
| Status | at `b6` |
| MCU version | constant `1.0` |

Bytes 8–10 (firmware date, BLE version) are a shared tail at fixed offsets for
every header family. `tempUnit` is constant `1` (°C). A `parseYigaoyun`
variant handles the `0x55`-header OEM brand with the same field set.

**Crypto note:** the lib also exports XTEA/TEA (`decrypt_tea`, 16-byte key in
`.rodata`), but it is **not on the advert parse path** — broadcast telemetry
is plaintext.

---

## Family C — Sysgration (`com.sysgration.tpms.app`)

Each sensor transmits a **standard Apple-iBeacon-format** manufacturer AD; the
app uses AltBeacon with layout `m:2-3=0215,i:4-19,i:20-21,i:22-23,p:24-24`.

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Mfr-data bytes 2–3 | `02 15` | iBeacon indicator |
| Company ID | **unconstrained** — any value passes | the actual CID the hardware emits is not pinned by the app (report open item); likely `0x004C` (Apple) as with most iBeacon-format devices, but unverified |
| Proximity UUID | `b54adc00-67f9-11d9-9669-0800200c9a66` | family T1 |
| | `b54adc00-67f9-11d9-9669-0800200c9a67` | family T2 |
| | `b54adc00-67f9-11d9-9669-0800200c9a6a` | family T3 |

Trap: `9e0271ef-…`, `a26f546b-…`, `fa8864a2-…` in the app are AltBeacon
`Region` label strings, **never transmitted**.

### Byte layout (offsets into the manufacturer value, CID at 0–1)

| Offset | Field | Size | Decode |
|--------|-------|------|--------|
| 0–1 | Company ID | 2 | not matched |
| 2–3 | iBeacon type/length | 2 | `02 15` |
| 4–19 | Proximity UUID | 16 | family selector (low byte `a66`/`a67`/`a6a`) |
| 20–21 | **Major = Sensor ID** | uint16 BE | persistent per tire; app displays `"<alarm bit><4-hex major>"` |
| 22 | **Minor high = temp + flags** | 1 | bit 7 = alarm; bit 6 = pressure 9th bit (T2/T3 only); rest = temperature code |
| 23 | **Minor low = pressure** | 1 | see below |
| 24 | Measured TX power | int8 | not decoded by the app |

| Family | Temperature (°C) | Pressure (kPa) | Battery-low sentinel | Secondary sentinel | Clamp |
|--------|------------------|----------------|----------------------|--------------------|-------|
| T1 `…a66` | `(b22 & 0x7F) − 40` | `b23 × 2.5` | temp == 87 (`0x7F`) | 86 | > 87 → 85 |
| T2 `…a67` | `(b22 & 0x3F) × 2 − 40` | `(b23 \| (b22&0x40 ? 0x100 : 0)) × 2.5` | temp == 86 (`0x3F`) | 84 | > 82 → 82 |
| T3 `…a6a` | `(b22 & 0x3F) × 3 − 40` | same 9-bit form as T2 | temp == 149 (`0x3F`) | 146 | > 143 → 143 |

An all-ones temperature field means **battery low**, not a real temperature.
The app's "decompression error" flag is derived from rate-of-change across
frames, not from one advert.

**GATT-only side accessory:** a "voice-controller dongle" discovered by name
prefix `TPMS_` (service `0xED01`, notify `0xFD01`, write `0xFD02`) is connected
to, not a tire sensor. Note that its `TPMS_` name **also matches the existing
`tpms.py` name pattern**.

---

## Family D — TireMinder (`com.minderresearch.tiremindertpms`)

Architecturally different: the per-tire sensors are **433 MHz** (invisible to
BLE). A BLE **signal booster** relays their data to the phone over GATT.

| Signal | Value | Notes |
|--------|-------|-------|
| Local name | `TM-Blue22` (exact, fixed) | the only passive signature; also the Nordic-DFU target name |
| Service UUID | `6E400001-B5A3-F393-E0A9-E50E24DCCA9E` | Nordic UART Service — generic, see [nordic-uart-service.md](nordic-uart-service.md) |
| Manufacturer / service data | none | |

All tire data rides NUS notify `6E400003-…` after connecting (plaintext, no
auth) — out of passive scope.

---

## What We Can Parse from Advertisements

| Field | A Chaoyue | B AiCare | C Sysgration | D TireMinder |
|-------|-----------|----------|--------------|--------------|
| Per-tire sensor ID | 3 B | — (MAC only) | 16-bit major | — |
| Pressure | kPa | yes (unit code) | kPa | — |
| Temperature | °C | °C | °C | — |
| Battery | level byte | volts | low-flag sentinel | — |
| Alarm / leak | status byte | status byte | alarm bit | — |
| Firmware info | — | MCU ver, BLE ver, fw date | — | — |
| Presence of RV/trailer booster | — | — | — | yes |

## What Requires GATT

- Family D: all tire telemetry (NUS).
- Family C: the dongle's configuration channel only.
- Families A/B: nothing — the apps never connect to a sensor.

## Identity Hashing

```
A: SHA256("tpms_chaoyue:" + sensor_id_hex)[:16]        # 3-byte ID, stable across MAC changes
B: SHA256("tpms_aicare:" + mac)[:16]                   # app keys on MAC (getDeviceId(mac)); no payload ID
C: SHA256("tpms_sysgration:" + family + major_hex)[:16]
D: SHA256("tireminder:" + mac)[:16]
```

The reports found no RPA / address-rotation evidence for any family; a vehicle
is effectively identified by its set of 4 (or more) sensor IDs/MACs.

## Detection Significance

- **Vehicle tracking.** Persistent, unencrypted per-tire IDs make a car's
  sensor set a long-lived fingerprint (classic TPMS tracking) — axle/trailer
  counting too.
- **Activity inference.** Warm tires ⇒ recently driven; falling pressure ⇒
  slow leak; many sensors only beacon when moving, so presence itself is an
  activity signal.
- **Spoofable.** No auth anywhere; families A/C need only a forged frame
  (family B adds an attacker-computable checksum). apk-ble-hunting's batch-27
  audit rates this LOW-MEDIUM: these are **advisory** aftermarket displays,
  not ECU inputs, and a convincing per-tire spoof also needs MAC spoofing.
- **TireMinder** leaks only "an RV/trailer with this booster is here" + a
  trackable MAC.

## Plugin gaps

Future plugin work (not implemented here):

1. **Family A mis-decode in `tpms.py`.** Names containing `TPMS` (e.g.
   `TPMS1_…`) match `tpms.py`'s `^(TPMS|BR)` pattern, and the plugin will
   decode the 16-byte payload with its own layout (sensor_index = payload[0],
   etc.) — producing garbage. Its `company_id=0x0001` registration does **not**
   match family A on the wire (CID `0x0100`). A family-A decoder should gate on
   CID `0x0100` (wire `00 01`) + 16-byte payload (+ optionally `TPMS` name) and
   decode sensor ID / LE32 pressure / LE32 temp / battery / status; `tpms.py`
   should stand down for it. *Needs a live capture to confirm the framing
   inference before relying on it.*
2. **Family B**: new matcher on service UUID `0xFBB0`/`0xFBC0` + mfr value
   ≥ 11 B; verify checksum, decode per header family.
3. **Family C**: iBeacon parser will claim these today (as generic iBeacons);
   a TPMS path keyed on the three `b54adc00-…` proximity UUIDs should decode
   major/minor. The dongle's `TPMS_` name also hits `tpms.py`.
4. **Family D**: name-only presence match `^TM-Blue22$`.

## References

- apk-ble-hunting `reports/chaoyue-acartpms_passive.md` (`MainService.java:59,124,128`; `DataHandleTool.java:17,88,92,96-111`)
- apk-ble-hunting `reports/chaoyue-tyed_passive.md` (`MainService.java:37,201,226,244-291`; `MainActivity.java:864-881,1879-1884,4213-4224`; `SPUtils.java:8,108`)
- apk-ble-hunting `reports/aicare-net-cn-itpms_passive.md` and `aicare-net-cn-itpms_native.md` (`TpmsScan.java:36-37,79-82,130,170`; `ScanService.java:230-239`; `libtpms-lib.so` `parse@0xda0`)
- apk-ble-hunting `reports/sysgration-tpms-app_passive.md` (`ServiceScan.java:44-50,141-240,700`; `e2.java:20`; dongle `d0.java:1003`)
- apk-ble-hunting `reports/minderresearch-tiremindertpms_passive.md` (`MainActivity.java:2468,2480`; `BleServerContant.java:31-34`)
- apk-ble-hunting `reports/_audit_batch27.md` §D/E (spoofing severity calibration)
- adwatch `src/adwatch/plugins/tpms.py`, `src/adwatch/plugins/fobo_tpms.py`
