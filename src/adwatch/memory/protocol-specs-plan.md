# Protocol Specs — Implementation Plan

## Overview
Persist HexViewer field definitions to SQLite so they survive page reloads and can be shared, auto-loaded when viewing similar ads, and used to generate @register_parser plugin skeletons.

## 5 Phases

### Phase 1: Storage Layer (`storage/specs.py`)

**Tables** (added in `migrations.py`):

```sql
CREATE TABLE IF NOT EXISTS protocol_specs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    company_id INTEGER,          -- match criterion (OR logic)
    service_uuid TEXT,           -- match criterion (OR logic)
    local_name_pattern TEXT,     -- match criterion (OR logic, regex)
    data_source TEXT DEFAULT 'mfr',  -- 'mfr' or 'svc'
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS protocol_spec_fields (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    spec_id INTEGER NOT NULL REFERENCES protocol_specs(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    offset INTEGER NOT NULL,
    length INTEGER NOT NULL,
    field_type TEXT NOT NULL,     -- uint8, uint16, uint32, int8, int16, int32, float32, utf8, mac_addr, uuid, bitfield, raw_hex
    endian TEXT DEFAULT 'LE',     -- LE or BE
    description TEXT,
    sort_order INTEGER DEFAULT 0,
    UNIQUE(spec_id, name)
);
```

**SpecStorage class** (`storage/specs.py`):
- `create_spec(name, description, company_id, service_uuid, local_name_pattern, data_source)` → spec dict
- `update_spec(spec_id, **kwargs)` → updated spec dict
- `delete_spec(spec_id)` → None (CASCADE deletes fields)
- `get_spec(spec_id)` → spec dict with fields list
- `list_specs()` → list of spec dicts (without fields)
- `match_specs(raw_ad_row)` → list of matching specs (OR logic on company_id, service_uuid, local_name_pattern — same matching logic as @register_parser)
- `add_field(spec_id, name, offset, length, field_type, endian, description)` → field dict
- `update_field(field_id, **kwargs)` → field dict
- `delete_field(field_id)` → None
- `get_fields(spec_id)` → list of field dicts ordered by sort_order/offset

### Phase 2: API Endpoints (added to `explorer.py` router)

**Spec CRUD:**
- `POST /api/explorer/specs` — Create spec (body: name, description, match criteria)
- `GET /api/explorer/specs` — List all specs
- `GET /api/explorer/specs/{spec_id}` — Get spec with fields
- `PUT /api/explorer/specs/{spec_id}` — Update spec metadata
- `DELETE /api/explorer/specs/{spec_id}` — Delete spec + cascade fields

**Field CRUD:**
- `POST /api/explorer/specs/{spec_id}/fields` — Add field
- `PUT /api/explorer/specs/{spec_id}/fields/{field_id}` — Update field
- `DELETE /api/explorer/specs/{spec_id}/fields/{field_id}` — Delete field

**Matching:**
- `GET /api/explorer/ad/{ad_id}/specs` — Return specs matching this ad (by company_id / service_uuid / local_name)

### Phase 3: Code Generation (`codegen.py`)

**`generate_parser(spec)` → str:**
Generate a complete @register_parser plugin .py file from a spec:
```python
"""Auto-generated parser for {spec.name}."""
import hashlib
from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser

@register_parser(
    name="{spec.name}",
    company_id={spec.company_id},       # if set
    service_uuid="{spec.service_uuid}", # if set
    local_name_pattern=r"{spec.local_name_pattern}", # if set
    description="{spec.description}",
    version="1.0.0",
    core=False,
)
class {ClassName}Parser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        data = raw.manufacturer_data  # or service_data based on data_source
        if not data or len(data) < {min_required_length}:
            return None

        # Field extractions from spec
        {field_name} = struct.unpack_from('{format}', data, {offset})[0]
        ...

        id_hash = hashlib.sha256(f"{spec.name}:{{raw.mac_address}}".encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="{spec.name}",
            beacon_type="{spec.name}",
            device_class="unknown",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata={{ {field_extractions} }},
        )
```

**Helpers:**
- `_type_to_struct(field_type, endian)` — Map field_type + endian to struct format string
- `_snake_to_class(name)` — Convert snake_case to PascalCase for class name
- `_min_data_length(fields)` — Calculate minimum byte length from max(offset + length)

**Endpoint:**
- `GET /api/explorer/specs/{spec_id}/codegen` — Returns generated Python code as text/plain

### Phase 4: Frontend Integration (in `index.html`)

**HexViewer changes:**
- "Save to Spec" button: saves current fields to a protocol spec
  - If no spec loaded: prompt for name + match criteria → POST /api/explorer/specs + POST fields
  - If spec loaded: PUT updated fields
- "Load Spec" dropdown: shows matching specs for current ad → loads fields into HexViewer
- Auto-load: when opening an ad in HexViewer, auto-fetch matching specs via `GET /api/explorer/ad/{id}/specs`
- Visual indicator when viewing a spec (spec name badge, "unsaved changes" state)

**ExplorerTab changes:**
- "Specs" sub-panel: list all specs, click to view/edit
- "Generate Parser" button on spec detail → fetch codegen → display in modal with copy button

### Phase 5: Wiring & Polish

- Auto-load matching spec when navigating to HexViewer detail
- Spec name shown in explorer list for matched ads
- Export spec as JSON (download)
- Import spec from JSON (upload)
- Spec field validation (overlapping offsets warning, out-of-bounds warning)

## Files

**New:**
- `src/adwatch/storage/specs.py` — SpecStorage class
- `src/adwatch/codegen.py` — Parser code generation
- `tests/test_spec_storage.py` — Storage layer tests
- `tests/test_spec_api.py` — API endpoint tests
- `tests/test_codegen.py` — Code generation tests

**Modified:**
- `src/adwatch/storage/migrations.py` — Add protocol_specs + protocol_spec_fields tables
- `src/adwatch/dashboard/routers/explorer.py` — Add spec/field CRUD + matching + codegen endpoints
- `src/adwatch/dashboard/app.py` — Pass db to explorer router for SpecStorage
- `src/adwatch/dashboard/frontend/index.html` — HexViewer save/load, spec management UI

## Build Order (for TDD)

Build Phases 1–3 first (storage, API, codegen) — these are backend-only and fully testable. Phase 4–5 (frontend) can follow in a separate pass.

### Iteration 1: Phase 1 (Storage)
- Tests: CRUD operations, matching logic, cascading deletes, field ordering
- Code: specs.py, migrations.py changes

### Iteration 2: Phase 2 (API)
- Tests: All endpoints with httpx, error cases (404, validation)
- Code: explorer.py additions, app.py wiring

### Iteration 3: Phase 3 (Codegen)
- Tests: Generated code validity (ast.parse), struct format mapping, edge cases
- Code: codegen.py
