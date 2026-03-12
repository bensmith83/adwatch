# Protocol Explorer — Implementation Plan

## Overview
A first-class dashboard tab (like Overview/Plugins) for interactively exploring BLE advertisement payloads. Browse all raw ads, filter/group, inspect hex bytes with click-to-select highlighting, label fields with data types, compare multiple ads to spot patterns, and eventually generate parser skeletons.

## Scope: Phases 1+2 (initial build)

### Backend: `dashboard/routers/explorer.py`

**Endpoints:**

1. `GET /api/explorer/ads` — Browse & filter
   - Query params:
     - `ad_type` (str, optional) — filter by ad_type, or `__null__` for unclassified
     - `parsed_by` (str, optional) — `__null__` for unparsed, or specific parser name
     - `company_id` (int, optional) — filter by company_id extracted from manufacturer_data_hex
     - `service_uuid` (str, optional) — filter by service UUID in service_uuids_json
     - `local_name` (str, optional) — substring match on local_name
     - `mac_prefix` (str, optional) — prefix match on mac_address
     - `min_sightings` (int, default=1) — only show ads seen at least N times
     - `limit` (int, default=100, max=500)
     - `group_by` (str, optional) — `company_id` or `ad_type` to cluster similar payloads
   - Returns: list of raw_advertisement rows + derived fields:
     - `company_id_int` (extracted from manufacturer_data_hex)
     - `payload_hex` (manufacturer_data without company_id prefix)
     - `payload_length` (byte count)

2. `GET /api/explorer/ad/{id}` — Single ad detail
   - Returns full row with all fields + decoded service_data

3. `GET /api/explorer/facets` — Filter options
   - Returns distinct ad_types, company_ids (with counts), service_uuids, top local_names
   - Powers the filter dropdowns

4. `GET /api/explorer/compare` — Multi-ad comparison
   - Query param: `ids` (comma-separated ad IDs)
   - Returns aligned payloads + diff analysis:
     - For each byte position: `{offset, values: [byte_per_ad], is_constant: bool}`
   - Auto-detects: constant bytes, incrementing counters, random/changing bytes

### Frontend: New components in `index.html`

**NavBar change:** Add static "Explorer" button next to Overview and Plugins.

**Components:**

1. **ExplorerTab** — Main container
   - State: filters, selected ads, active panel (list/detail/compare)
   - Fetches facets on mount for filter dropdowns

2. **ExplorerFilters** — Filter bar
   - Dropdowns: ad_type (from facets), parsed status (all/unparsed/specific parser)
   - Text inputs: company_id, service_uuid, local_name, mac_prefix
   - Slider/input: min_sightings
   - Toggle: "Group by company_id" mode
   - "Watch" toggle — streams live matching ads via WebSocket

3. **ExplorerList** — Results table
   - Columns: MAC, ad_type, parsed_by, sightings, payload preview (first 16 bytes), payload length, RSSI, local_name
   - Click row → opens HexViewer for that ad
   - "Compare selected" button → takes top N from current filter (or manually picked) into CompareView
   - Sortable columns (sighting_count, last_seen, payload_length)

4. **HexViewer** — Interactive byte inspector (THE core component)
   - Layout: hex grid (16 bytes per row, offset gutter on left)
   - Shows manufacturer_data OR service_data (tab selector if both present)
   - **Click a byte** → select it (highlighted)
   - **Click-drag** → select a range of bytes (highlighted in a color)
   - **Right panel**: Field editor
     - For current selection: name input, data type dropdown, endianness toggle
     - Data types: `uint8`, `uint16`, `uint32`, `int8`, `int16`, `int32`, `float32`, `utf8`, `mac_addr`, `uuid`, `bitfield`, `raw_hex`
     - Endianness: LE (default) / BE toggle
     - **Live decode**: Shows the decoded value as you select bytes + pick type
   - **Color-coded selections**: Each labeled field gets a distinct color
   - **Field list**: Below hex grid, shows all defined fields as a table:
     `| Color | Name | Offset | Length | Type | Decoded Value |`
   - Session state only (no persistence yet)
   - ASCII column alongside hex (printable chars shown, others as `.`)

5. **CompareView** — Multi-ad byte alignment
   - Stacks payloads vertically, byte-aligned
   - Color coding:
     - Green: constant across all selected ads
     - Yellow: varies but in a pattern (increments, limited set)
     - Red: appears random/unique per ad
   - Summary row at bottom: `[C]onstant / [V]ariable / [R]andom` per byte position
   - Clicking a column selects that byte offset → can label it in HexViewer
   - Top N from filtered results (default 10), with ability to add/remove specific ads

6. **WatchMode** — Live incoming ads
   - When "Watch" is toggled on:
     - Subscribe to WebSocket `sighting_batch` events
     - Filter incoming ads client-side to match current filter criteria
     - Append matching ads to a separate "Live" section at top of list
     - Cap at 50 live entries
   - Useful for seeing new instances of a protocol in real-time

### CSS additions
- `.hex-grid` — monospace grid layout for hex bytes
- `.hex-byte` — individual byte cell (hover, selected, field-colored states)
- `.hex-offset` — gutter with byte offsets
- `.hex-ascii` — ASCII representation column
- `.field-highlight-N` — 8-10 distinct highlight colors for field selections
- `.compare-row` — stacked comparison row
- `.byte-constant`, `.byte-variable`, `.byte-random` — diff highlighting

### WebSocket changes
- No backend changes needed for Phase 1-2
- Watch mode uses existing `sighting_batch` events, filters client-side

### Files to create/modify

**New files:**
- `src/adwatch/dashboard/routers/explorer.py` — Backend API
- (All frontend in existing `index.html`)

**Modified files:**
- `src/adwatch/dashboard/app.py` — Mount explorer router
- `src/adwatch/dashboard/frontend/index.html` — Add Explorer tab + all components + CSS
- `src/adwatch/storage/raw.py` — Add explorer-specific query methods (facets, compare)

**Test files:**
- `tests/test_explorer_api.py` — Backend endpoint tests
- `tests/test_explorer_queries.py` — Storage query tests

## Data flow

```
User opens Explorer tab
  → GET /api/explorer/facets → populate filter dropdowns
  → User adjusts filters
  → GET /api/explorer/ads?... → show results table
  → User clicks a row
  → GET /api/explorer/ad/{id} → show in HexViewer
  → User selects bytes, labels fields
  → User clicks "Compare"
  → GET /api/explorer/compare?ids=... → show CompareView
  → User toggles "Watch"
  → WebSocket sighting_batch → client-side filter → append to live list
```

## Phase 3+ (deferred)
- Persist field definitions to `protocol_specs` SQLite table
- "Generate Parser" → Python skeleton with @register_parser + field extraction
- Export/import protocol specs as JSON
- Auto-suggest field boundaries based on comparison analysis
- Bit-level viewer for bitfield types
