# Zipcar In-Car Telematics Beacon (CID 0x036C)

## Overview

Zipcar holds Bluetooth SIG **company identifier `0x036C`**. Every US
Zipcar carries an in-car telematics unit — FCC ID **2AYUAM400**, model
M400: an ST BlueNRG-M0A BLE module paired with a Telit LE910C cellular
modem — which the member app uses for phone-based lock/unlock. A frame
under this CID is therefore the **car itself** advertising, not a
personal device.

Two captures to date, a month apart (2026-08-01, 2026-08-30): one unit
and one sighting each, random addresses, no local name, no service
data — consistent with a Zipcar parked or driving past.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x036C` (wire `6c 03`) | SIG-assigned to Zipcar |
| Payload length | exactly 7 bytes | hard gate |
| Byte [0] | `0x01` | format/version byte, gated on |

### Byte Layout (7 bytes, 2 observed records)

```
Offset  Size  Field
------  ----  -----
0       1     Format/version (0x01 on both units)
1–6     6     Opaque token — identifier-shaped, differs per unit,
              surfaced raw
```

Observed frames: `6c 03 | 01 | 42 c1 ae da c2 7a` and
`6c 03 | 01 | 41 0b 14 9a 1a 04`. The 6-byte token is **not** decoded
as a MAC or VIN and is **not** used as a stable device key: with one
sighting per unit there is no evidence it is stable per vehicle across
encounters (it could equally be a rotating pairing token for the app
handshake).

## Parser Scope (Passive Only)

`ZipcarParser` (`zipcar`, deviceClass `vehicle`) in the NearSight app:

- Gates on CID 0x036C AND 7-byte payload AND leading `0x01`. Any other
  0x036C shape is left unclaimed until captured.
- Emits `frame_version` and the raw `token_hex`.
- Identity keys on the (rotating) MAC; no stableKey.

## Attribution Confidence

**Vendor: high** — the SIG registry entry is authoritative and the
in-car BLE hardware is FCC-documented. **Everything else: low** — two
frames from two units, one sighting each. The version-byte gate holds
on 2/2 units; the token's per-vehicle stability is unknown, and a
watchlist bead (nearsight-11vs) tracks revisiting the stable-key
question when more sightings land.

## References

- Bluetooth SIG Assigned Numbers — company identifier 0x036C
- [FCC ID 2AYUAM400 — Zipcar In-car Telematics Device M400](https://fccid.io/2AYUAM400)
- [Zipcar support — locking and unlocking via the app](https://support.zipcar.com/hc/en-us/articles/360033129293-How-do-I-lock-unlock-my-Zipcar)
- NearSight app research write-up `research/sweep-2026-08-31-candidates.md`
