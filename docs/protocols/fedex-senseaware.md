# FedEx SenseAware ID / TRON ID Node Plugin

## Overview

Bluetooth SIG company ID `0x0141` is officially assigned to **FedEx Services**. The advertisement is emitted by FedEx's **SenseAware ID** and **TRON ID Node** BLE asset trackers — small battery-powered BLE tags affixed to packages moving through the FedEx Express network (First Overnight, Custom Critical, healthcare, aerospace, pharma). The tags broadcast every ~2 seconds and are read by gateway readers (Wi-Fi access points + dedicated fixed readers) deployed across FedEx sortation facilities and trucks. The TRON variant has its own FCC grant: FCC ID `2AKUXID2`, granted 2020-03-18, 2.402–2.48 GHz, Part 15C.

A fleet of these tags in a residential / commercial scan is essentially a snapshot of in-transit FedEx parcels in your physical proximity — receivable both inside FedEx infrastructure and out in the wild while a package is in transit or sitting on a porch.

This parser is, to the author's knowledge, the **first public decoder** of the SenseAware advertisement format. The inner extended record is exposed verbatim so reverse-engineering work can continue against it.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Company ID | `0x0141` (FedEx Services, SIG-assigned) |
| Local name | _absent_ — tags advertise anonymously |
| Service UUIDs | Some long-frame tags additionally list `0x180A` (Device Information) |

### Wire Format (TLV-nested)

Two variants observed in the wild:

**Short variant (10 bytes mfg data)** — beacon-only state:
```
Bytes 0..1  : 41 01                   ← SIG CID 0x0141 (FedEx Services), LE order
Bytes 2..3  : 07 0a                   ← TLV marker (frame type / version constant)
Bytes 4..9  : T1 T2 T3 T4 T5 T6       ← 6-byte tag identifier
```

**Extended variant (27 bytes mfg data)** — full state record:
```
Bytes 0..9   : same as short variant
Bytes 10..11 : 08 0c                  ← second TLV marker
Bytes 12..23 : R1..R12                ← 12-byte commissioning / sensor record
Bytes 24..26 : 00 00 00               ← zero-padding to fixed length
```

### Tag ID

The 6-byte field is the stable per-tag anchor. The leading-nibble pattern (`0x41`–`0x71`) matches Nordic-style random-static / non-resolvable address space, which is consistent with FedEx using disposable Nordic-class chips inside the tag and embedding the BLE address (or a derivative of it) directly into the advertisement so the cellular-uplinked gateway readers don't need to parse the BLE PDU header.

### Extended Record

The 12-byte `R1..R12` field of the extended variant is what the FedEx **SenseAware ID Node datasheet** describes as commissioning data plus a sensor sample (temperature / humidity / vibration on the higher-tier SKUs, location-update marker on the disposable ID Node). The exact byte layout is **not publicly documented** — we surface it as `extended_record` for future analysis.

Observed examples (from a 24-tag fleet capture):
```
c1860ba8c4e80107016615e4000000
df28ca100ef701070181 1ae4000000
ef9dd7437ef30107012c 4b93000000
```

The recurring `01 07 01` triplet at bytes 22..24 of the mfg data (or bytes 6..8 of the record) looks like a sub-TLV (`length=0x01 type=0x07 value=0x01`), suggesting the record itself is also TLV-encoded. Confirmation requires controlled captures against known SenseAware tag configurations.

## Detection Significance

- **Fleet density implies proximity to FedEx infrastructure.** A dense cluster of `0x0141 / 07 0a` advertisers strongly suggests you are scanning near a FedEx truck route, sortation hub, or a delivery in progress.
- **Stable tag IDs let you fingerprint individual parcels.** The 6-byte tag ID does not rotate while the tag is active, so a single tag can be tracked across captures even if its BD_ADDR rotates.
- **Privacy considerations.** The tags do not carry recipient, sender, or shipment metadata in the advertisement — those are looked up server-side via the gateway reader pipeline. The tag ID alone is not personally identifying, but a tag that consistently appears at a residential address over multiple days correlates with shipments to that address.

## What We Cannot Parse from Advertisements

- Shipment ID / sender / recipient / shipping route — all server-side, looked up by tag ID at FedEx gateway readers.
- Sensor samples (temperature, humidity, vibration) — likely encoded inside the 12-byte extended record but the format is undocumented.
- Battery / signal quality — same.

## References

- [Bluetooth SIG company identifiers (YAML mirror)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml) — confirms `0x0141` = FedEx Services.
- [FedEx newsroom: SenseAware ID launch](https://newsroom.fedex.com/newsroom/united-states-english/senseaware-id)
- [FCC ID `2AKUXID2` — "TRON ID Node with BLE"](https://fccid.io/2AKUXID2)
- [FCC ID `2AKUXM4` — SenseAware M4 (higher-tier sensor variant)](https://fccid.io/2AKUXM4)
- [SenseAware ID Node datasheet (FedEx CDN)](https://www.fedex.com/content/dam/fedex/us-united-states/senseaware/docs/SenseAware-ID-Node-DOC-090122.pdf)
- [BeaconZone blog — SenseAware BLE beaconing observed in the wild](https://www.beaconzone.co.uk/blog/fedex-senseaware-beacon/)
