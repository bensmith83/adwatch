# iBeacon Routing Bug

## Problem

The iBeacon parser registers with `company_id=0x004C` but the classifier/router extracts company_id from raw manufacturer_data bytes using little-endian byte order. When the manufacturer_data starts with `00 4c` (big-endian Apple company ID), the little-endian extraction yields `0x4C00` (19456) instead of `0x004C` (76).

This means **iBeacon advertisements are never routed to the iBeacon parser**, despite the parser itself handling both byte orders internally (lines 23–27 of `ibeacon.py`).

## Evidence

- 134,152 sightings in DB from 2 iBeacon ads with UUID `2686f39c-bada-4658-854a-a62e7e5e8b8d`
- `parsed_by` is NULL for all of them
- The parser code handles both LE and BE company IDs, but it never gets called

## Impact

- All iBeacon advertisements go unparsed
- Tilt Hydrometer (which uses iBeacon format) also goes unparsed
- Any iBeacon-based deployment is invisible to the parsed data view

## Fix Options

1. **Register with both byte orders**: Add `company_id=[0x004C, 0x4C00]` to `@register_parser`
2. **Fix the classifier**: Ensure the classifier tries both byte orders when extracting company_id from manufacturer_data
3. **Register without company_id filter**: Use a broader match and let the parser reject non-iBeacon ads internally (less efficient)

Option 1 is simplest and most targeted.

## Files

- `src/adwatch/parsers/ibeacon.py` — parser registration
- `src/adwatch/classifier.py` — company_id extraction logic
- `src/adwatch/registry.py` — routing logic
