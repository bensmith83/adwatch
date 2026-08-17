# Medical EKG Devices

> **⚠️ Status: retracted (2026-08-17).** The `EKG-XX-XX-XX` local-name family
> this doc described is **not a medical ECG monitor**. It is a Fellow "EKG"
> smart kettle (Stagg EKG / Corvo EKG line — "Electric Kettle Gooseneck") in
> Espressif Wi-Fi-provisioning mode. See [fellow.md](fellow.md) for the
> correct decoder and the evidence, and [alivecor-ekg.md](alivecor-ekg.md) for
> the genuine AliveCor Kardia identification.
>
> In short: the "custom service UUID" `021a9004-0382-4aea-bff4-6b3f1c5adfb4`
> is the Espressif BLE provisioning service (any ESP32 product in setup mode
> advertises it), and the second UUID this doc listed,
> `7aebf330-6cb1-46e4-b23b-7cc2262c605e`, is Fellow's aux service UUID from
> the decompiled Fellow app. The "medical device nearby" inference drawn from
> these sightings was wrong; the original attribution was a guess from the
> "EKG" token, as this doc's own "Known Manufacturers" section admitted.
>
> Parsers: adwatch `alivecor_ekg.py` v1.2.0 no longer claims `EKG-`; the
> family moved to `fellow.py` v1.1.0. NearSight `AliveCorParser` v2 is
> Kardia-only; `FellowKettleParser` owns `EKG-`. The example payload below is
> kept only so the misattribution is searchable.

## Original text (deprecated — see retraction above)

Portable EKG/ECG monitors broadcast BLE advertisements to enable pairing with companion mobile apps. These devices were believed to be identified by their `local_name` pattern (`EKG-XX-XX-XX`) which encodes part of the device's MAC address.

### Identification (as originally documented)

- **Local name pattern:** `^EKG-` (regex)
- **Example names:** `EKG-99-23-4c`, `EKG-A1-B2-C3`
- **Service UUIDs advertised:** `021a9004-0382-4aea-bff4-6b3f1c5adfb4` (= Espressif provisioning), `7aebf330-6cb1-46e4-b23b-7cc2262c605e` (= Fellow aux)

### Genuine medical ECG signals (for future work)

If real portable ECG monitors are to be catalogued, start from vendor-unique
signals rather than the "EKG" token:

- AliveCor Kardia: `ac060001-328c-a28f-9846-5a8aa212661b` (KardiaMobile 6L),
  `ac010001-328c-a28f-9846-5a8aa212661b` (KardiaCard), names
  `KardiaMobile_*` / `KardiaCard_*` — [alivecor-ekg.md](alivecor-ekg.md)
- Wellue / Viatom DuoEK, Eko stethoscopes, etc. — see the research-repo
  plugins `wellue_viatom.py`, `eko_stethoscope.py`
