"""Tests for Protocol Explorer frontend integration."""

import pytest
from httpx import ASGITransport, AsyncClient

from adwatch.dashboard.app import create_app
from adwatch.dashboard.websocket import WebSocketManager
from adwatch.models import RawAdvertisement, Classification
from adwatch.registry import ParserRegistry
from adwatch.storage.base import Database
from adwatch.storage.migrations import run_migrations
from adwatch.storage.raw import RawStorage


@pytest.fixture
async def db(tmp_path):
    database = Database()
    await database.connect(str(tmp_path / "test.db"))
    await run_migrations(database)
    yield database
    await database.close()


@pytest.fixture
async def raw_storage(db):
    return RawStorage(db)


@pytest.fixture
def registry():
    return ParserRegistry()


@pytest.fixture
def ws_manager():
    return WebSocketManager()


@pytest.fixture
async def client(raw_storage, registry, ws_manager):
    app = create_app(
        raw_storage=raw_storage,
        classifier=None,
        registry=registry,
        ws_manager=ws_manager,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def seeded_storage(raw_storage):
    """Seed two ads with manufacturer_data for explorer tests."""
    ad1 = RawAdvertisement(
        timestamp="2025-01-15T10:30:00+00:00",
        mac_address="AA:BB:CC:DD:EE:01",
        address_type="random",
        manufacturer_data=b"\x4c\x00\x10\x05\x01",
        service_data=None,
        rssi=-62,
    )
    ad2 = RawAdvertisement(
        timestamp="2025-01-15T10:30:01+00:00",
        mac_address="AA:BB:CC:DD:EE:02",
        address_type="random",
        manufacturer_data=b"\x4c\x00\x10\x05\x02",
        service_data=None,
        rssi=-70,
    )
    cls = Classification(ad_type="apple_nearby", ad_category="phone", source="company_id")
    await raw_storage.save(ad1, cls)
    await raw_storage.save(ad2, cls)
    return raw_storage


# --- HTML content tests (should FAIL — Explorer not yet in index.html) ---


@pytest.mark.asyncio
async def test_html_contains_explorer_nav_button(client):
    """HTML should have an Explorer nav button."""
    resp = await client.get("/")
    assert resp.status_code == 200
    html = resp.text
    # Look for "Explorer" inside a button element
    assert ">Explorer<" in html or ">Explorer</button>" in html


@pytest.mark.asyncio
async def test_html_contains_hex_grid_css(client):
    """HTML should define hex-grid, hex-byte, hex-offset, hex-ascii CSS classes."""
    resp = await client.get("/")
    html = resp.text
    for css_class in ["hex-grid", "hex-byte", "hex-offset", "hex-ascii"]:
        assert css_class in html, f"Missing CSS class: {css_class}"


@pytest.mark.asyncio
async def test_html_contains_explorer_components(client):
    """HTML should define ExplorerTab, HexViewer, CompareView, ExplorerFilters, ExplorerList."""
    resp = await client.get("/")
    html = resp.text
    for component in ["ExplorerTab", "HexViewer", "CompareView", "ExplorerFilters", "ExplorerList"]:
        assert component in html, f"Missing JS component: {component}"


@pytest.mark.asyncio
async def test_html_contains_field_highlight_css(client):
    """HTML should have field-highlight CSS classes for color-coded byte selections."""
    resp = await client.get("/")
    html = resp.text
    assert "field-highlight" in html


@pytest.mark.asyncio
async def test_html_contains_compare_diff_css(client):
    """HTML should have byte-constant, byte-variable, byte-random CSS classes."""
    resp = await client.get("/")
    html = resp.text
    for css_class in ["byte-constant", "byte-variable", "byte-random"]:
        assert css_class in html, f"Missing CSS class: {css_class}"


# --- API response shape tests (should PASS — backend already implemented) ---


@pytest.mark.asyncio
async def test_api_explorer_ads_response_shape(client, seeded_storage):
    """GET /api/explorer/ads returns items with company_id_int, payload_hex, payload_length."""
    resp = await client.get("/api/explorer/ads")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2
    for item in data:
        assert "company_id_int" in item
        assert "payload_hex" in item
        assert "payload_length" in item


@pytest.mark.asyncio
async def test_api_explorer_facets_response_shape(client, seeded_storage):
    """GET /api/explorer/facets returns dict with ad_types, company_ids, service_uuids, local_names."""
    resp = await client.get("/api/explorer/facets")
    assert resp.status_code == 200
    data = resp.json()
    for key in ["ad_types", "company_ids", "service_uuids", "local_names"]:
        assert key in data, f"Missing facets key: {key}"
    # ad_types and company_ids should be lists of dicts with value+count
    for facet_list in [data["ad_types"], data["company_ids"]]:
        assert isinstance(facet_list, list)
        if facet_list:
            assert "value" in facet_list[0]
            assert "count" in facet_list[0]


@pytest.mark.asyncio
async def test_api_explorer_compare_response_shape(client, seeded_storage):
    """GET /api/explorer/compare?ids=1,2 returns list of dicts with offset, values, is_constant."""
    resp = await client.get("/api/explorer/compare?ids=1,2")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    for entry in data:
        assert "offset" in entry
        assert "values" in entry
        assert "is_constant" in entry


@pytest.mark.asyncio
async def test_api_explorer_ad_detail_response_shape(client, seeded_storage):
    """GET /api/explorer/ad/{id} returns dict with manufacturer_data_hex and service_data_json."""
    resp = await client.get("/api/explorer/ad/1")
    assert resp.status_code == 200
    data = resp.json()
    assert "manufacturer_data_hex" in data
    assert "service_data_json" in data


# --- Polish feature tests (should FAIL — not yet implemented) ---


@pytest.mark.asyncio
async def test_watch_mode_filters_incoming_ads(client):
    """Watch mode should filter incoming ads against active filters (matchesFilters function)."""
    resp = await client.get("/")
    html = resp.text
    assert "matchesFilters" in html, "Watch mode should use a matchesFilters function to filter incoming ads"


@pytest.mark.asyncio
async def test_compare_view_column_click_navigates(client):
    """CompareView byte columns should be clickable to navigate to HexViewer."""
    resp = await client.get("/")
    html = resp.text
    assert "onSelectByte" in html, "CompareView should accept onSelectByte prop for column click navigation"


@pytest.mark.asyncio
async def test_compare_view_has_add_remove_controls(client):
    """CompareView should have controls to add and remove individual ads."""
    resp = await client.get("/")
    html = resp.text
    assert "onRemoveAd" in html, "CompareView should accept onRemoveAd prop"
    assert "onAddAd" in html, "CompareView should accept onAddAd prop"


# --- TLV structure analysis tests (should FAIL — not yet implemented) ---


@pytest.mark.asyncio
async def test_hex_viewer_has_tlv_buttons(client):
    """HexViewer should have Mark as Type and Mark as Length buttons."""
    resp = await client.get("/")
    html = resp.text
    assert "Mark as Type" in html, "HexViewer should have a 'Mark as Type' button"
    assert "Mark as Length" in html, "HexViewer should have a 'Mark as Length' button"


@pytest.mark.asyncio
async def test_hex_viewer_has_tlv_state(client):
    """HexViewer should manage TLV groups state."""
    resp = await client.get("/")
    html = resp.text
    assert "tlvGroups" in html, "HexViewer should have tlvGroups state"


@pytest.mark.asyncio
async def test_hex_viewer_has_tlv_css(client):
    """HTML should have TLV visual styling CSS classes."""
    resp = await client.get("/")
    html = resp.text
    for css_class in ["tlv-band", "tlv-level-0", "tlv-level-1", "tlv-level-2"]:
        assert css_class in html, f"Missing TLV CSS class: {css_class}"


@pytest.mark.asyncio
async def test_hex_viewer_has_tlv_tree(client):
    """HexViewer should have a TLV tree view section."""
    resp = await client.get("/")
    html = resp.text
    assert "tlv-tree" in html, "HexViewer should have a TLV tree view"


@pytest.mark.asyncio
async def test_hex_viewer_has_tlv_byte_markers(client):
    """HTML should have CSS for distinguishing T and L bytes."""
    resp = await client.get("/")
    html = resp.text
    assert "tlv-type-byte" in html, "Missing tlv-type-byte CSS class"
    assert "tlv-length-byte" in html, "Missing tlv-length-byte CSS class"


# --- Protocol Specs frontend integration tests (should FAIL — not yet implemented) ---


@pytest.mark.asyncio
async def test_hex_viewer_has_save_spec_button(client):
    """HexViewer should have a Save Spec button to persist field definitions."""
    resp = await client.get("/")
    html = resp.text
    assert "Save Spec" in html or "Save to Spec" in html, \
        "HexViewer should have a 'Save Spec' or 'Save to Spec' button"


@pytest.mark.asyncio
async def test_hex_viewer_has_load_spec_ui(client):
    """HexViewer should have UI to load a spec's fields."""
    resp = await client.get("/")
    html = resp.text
    assert "Load Spec" in html or "spec-dropdown" in html or "loadSpec" in html, \
        "HexViewer should have spec loading UI (Load Spec text or spec dropdown)"


@pytest.mark.asyncio
async def test_hex_viewer_has_spec_indicator(client):
    """HexViewer should show which spec is currently loaded."""
    resp = await client.get("/")
    html = resp.text
    assert "spec-badge" in html or "loaded-spec" in html or "specName" in html, \
        "HexViewer should have a spec name badge/indicator element"


@pytest.mark.asyncio
async def test_hex_viewer_fetches_matching_specs(client):
    """HexViewer should auto-load matching specs via the ad specs endpoint."""
    resp = await client.get("/")
    html = resp.text
    assert "/api/explorer/ad/" in html and "/specs" in html, \
        "HexViewer should fetch matching specs from /api/explorer/ad/{id}/specs"


@pytest.mark.asyncio
async def test_hex_viewer_has_unsaved_indicator(client):
    """HexViewer should indicate when field definitions have unsaved changes."""
    resp = await client.get("/")
    html = resp.text
    assert "unsaved" in html.lower() or "unsavedChanges" in html or "spec-modified" in html, \
        "HexViewer should have an unsaved changes indicator"


@pytest.mark.asyncio
async def test_explorer_has_specs_panel(client):
    """Explorer should have a Specs panel option in the navigation."""
    resp = await client.get("/")
    html = resp.text
    assert ">Specs<" in html or ">Specs</button>" in html or '"Specs"' in html, \
        "Explorer should have a 'Specs' panel/nav option"


@pytest.mark.asyncio
async def test_specs_panel_lists_specs(client):
    """Specs panel should fetch the list of all specs."""
    resp = await client.get("/")
    html = resp.text
    assert "/api/explorer/specs" in html, \
        "Specs panel should fetch spec list from /api/explorer/specs"


@pytest.mark.asyncio
async def test_specs_panel_has_delete(client):
    """Specs panel should have delete functionality for specs."""
    resp = await client.get("/")
    html = resp.text
    assert "deleteSpec" in html or "Delete Spec" in html or "onDeleteSpec" in html, \
        "Specs panel should have spec delete functionality"


@pytest.mark.asyncio
async def test_specs_panel_has_generate_parser(client):
    """Specs panel should have a Generate Parser button."""
    resp = await client.get("/")
    html = resp.text
    assert "Generate Parser" in html or "generateParser" in html or "Generate" in html, \
        "Specs panel should have a 'Generate Parser' button"


@pytest.mark.asyncio
async def test_codegen_display_has_copy(client):
    """Codegen display should have copy-to-clipboard functionality."""
    resp = await client.get("/")
    html = resp.text
    assert "copyCode" in html or "Copy to Clipboard" in html or "writeText" in html, \
        "Codegen display should have copy-to-clipboard functionality"


@pytest.mark.asyncio
async def test_codegen_display_uses_pre(client):
    """Codegen display should use a preformatted block for generated code."""
    resp = await client.get("/")
    html = resp.text
    assert "codegen-output" in html or "generated-code" in html or "codegenPre" in html, \
        "Codegen display should have a dedicated pre block for code output"


@pytest.mark.asyncio
async def test_codegen_fetches_from_api(client):
    """Codegen display should fetch generated code from the codegen endpoint."""
    resp = await client.get("/")
    html = resp.text
    assert "/codegen" in html, \
        "Codegen display should fetch from the /codegen API endpoint"


@pytest.mark.asyncio
async def test_specs_panel_has_export(client):
    """Specs panel should have an Export button for spec JSON export."""
    resp = await client.get("/")
    html = resp.text
    assert "Export" in html or "exportSpec" in html, \
        "Specs panel should have Export functionality"


@pytest.mark.asyncio
async def test_specs_panel_has_import(client):
    """Specs panel should have an Import button for spec JSON import."""
    resp = await client.get("/")
    html = resp.text
    assert "Import" in html or "importSpec" in html, \
        "Specs panel should have Import functionality"


@pytest.mark.asyncio
async def test_hex_viewer_save_field_marks_unsaved(client):
    """saveField function should set unsaved state."""
    resp = await client.get("/")
    html = resp.text
    # The saveField function body should reference unsaved/setUnsavedChanges
    assert "saveField" in html
    # Find the saveField function and verify it sets unsaved state
    idx = html.index("saveField")
    # Look within reasonable distance for setUnsavedChanges or unsaved
    chunk = html[idx:idx+500]
    assert "setUnsavedChanges(true)" in chunk or "setUnsaved" in chunk
