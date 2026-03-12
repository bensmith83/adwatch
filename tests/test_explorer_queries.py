"""Tests for Protocol Explorer storage layer (RawStorage explorer methods)."""

import pytest

from adwatch.models import RawAdvertisement, Classification
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


def _make_ad(mac, manufacturer_data=None, service_uuids=None, local_name=None,
             rssi=-60, service_data=None, timestamp="2025-01-15T10:30:00+00:00"):
    return RawAdvertisement(
        timestamp=timestamp,
        mac_address=mac,
        address_type="random",
        manufacturer_data=manufacturer_data,
        service_data=service_data,
        service_uuids=service_uuids or [],
        local_name=local_name,
        rssi=rssi,
    )


# --- Seed helper ---

async def _seed_diverse_ads(raw_storage):
    """Insert a variety of ads for testing filters/facets."""
    # Apple ad (company_id 0x004C = 76)
    apple_ad = _make_ad("AA:BB:CC:DD:EE:01", manufacturer_data=b"\x4c\x00\x10\x05\x01")
    await raw_storage.save(apple_ad, Classification("apple_nearby", "phone", "company_id"),
                           parsed_by=["apple_continuity"])

    # Microsoft CDP ad (company_id 0x0006 = 6)
    ms_ad = _make_ad("MS:CD:P0:00:00:01", manufacturer_data=b"\x06\x00\x01\x09\x20")
    await raw_storage.save(ms_ad, Classification("microsoft_cdp", "laptop", "company_id"),
                           parsed_by=["microsoft_cdp"])

    # Fast Pair ad (service UUID, no manufacturer_data)
    fp_ad = _make_ad(
        "FA:57:PA:1R:00:01",
        service_data={"0000fe2c-0000-1000-8000-00805f9b34fb": b"\xAA\xBB"},
        service_uuids=["0000fe2c-0000-1000-8000-00805f9b34fb"],
    )
    await raw_storage.save(fp_ad, Classification("google_fast_pair", "audio", "service_uuid"),
                           parsed_by=["fast_pair"])

    # ThermoPro ad (local_name only, no manufacturer_data)
    tp_ad = _make_ad("11:22:33:44:55:66", local_name="TP357 (2B54)")
    await raw_storage.save(tp_ad, Classification("thermopro", "sensor", "local_name"),
                           parsed_by=["thermopro"])

    # Unknown ad (no classification, no parser)
    unk_ad = _make_ad("00:11:22:33:44:55", manufacturer_data=b"\xff\xff\x01\x02\x03")
    await raw_storage.save(unk_ad)

    return 5  # total count


# ===================================================================
# explorer_query() tests
# ===================================================================

class TestExplorerQuery:
    @pytest.mark.asyncio
    async def test_returns_all_ads_no_filters(self, raw_storage):
        count = await _seed_diverse_ads(raw_storage)
        results = await raw_storage.explorer_query()
        assert len(results) == count

    @pytest.mark.asyncio
    async def test_filter_by_ad_type(self, raw_storage):
        await _seed_diverse_ads(raw_storage)
        results = await raw_storage.explorer_query(ad_type="apple_nearby")
        assert len(results) == 1
        assert results[0]["ad_type"] == "apple_nearby"

    @pytest.mark.asyncio
    async def test_filter_by_ad_type_null(self, raw_storage):
        """__null__ should return ads with no classification."""
        await _seed_diverse_ads(raw_storage)
        results = await raw_storage.explorer_query(ad_type="__null__")
        assert len(results) == 1
        assert results[0]["ad_type"] is None

    @pytest.mark.asyncio
    async def test_filter_by_parsed_by(self, raw_storage):
        await _seed_diverse_ads(raw_storage)
        results = await raw_storage.explorer_query(parsed_by="apple_continuity")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_filter_by_parsed_by_null(self, raw_storage):
        """__null__ should return ads that were not parsed by anything."""
        await _seed_diverse_ads(raw_storage)
        results = await raw_storage.explorer_query(parsed_by="__null__")
        assert len(results) == 1
        assert results[0]["parsed_by"] is None

    @pytest.mark.asyncio
    async def test_filter_by_company_id(self, raw_storage):
        """Filter by integer company_id (extracted from manufacturer_data first 2 bytes LE)."""
        await _seed_diverse_ads(raw_storage)
        # Apple company_id = 0x004C = 76
        results = await raw_storage.explorer_query(company_id=76)
        assert len(results) == 1
        assert results[0]["mac_address"] == "AA:BB:CC:DD:EE:01"

    @pytest.mark.asyncio
    async def test_filter_by_service_uuid(self, raw_storage):
        await _seed_diverse_ads(raw_storage)
        results = await raw_storage.explorer_query(service_uuid="fe2c")
        assert len(results) == 1
        assert results[0]["mac_address"] == "FA:57:PA:1R:00:01"

    @pytest.mark.asyncio
    async def test_filter_by_local_name(self, raw_storage):
        await _seed_diverse_ads(raw_storage)
        results = await raw_storage.explorer_query(local_name="TP357")
        assert len(results) == 1
        assert results[0]["local_name"] == "TP357 (2B54)"

    @pytest.mark.asyncio
    async def test_filter_by_mac_prefix(self, raw_storage):
        await _seed_diverse_ads(raw_storage)
        results = await raw_storage.explorer_query(mac_prefix="AA:BB")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_filter_by_min_sightings(self, raw_storage):
        await _seed_diverse_ads(raw_storage)
        # Save same ad again to bump sighting_count to 2
        apple_ad = _make_ad("AA:BB:CC:DD:EE:01", manufacturer_data=b"\x4c\x00\x10\x05\x01",
                            timestamp="2025-01-15T10:31:00+00:00")
        await raw_storage.save(apple_ad, Classification("apple_nearby", "phone", "company_id"))

        results = await raw_storage.explorer_query(min_sightings=2)
        assert len(results) == 1
        assert results[0]["sighting_count"] >= 2

    @pytest.mark.asyncio
    async def test_limit(self, raw_storage):
        await _seed_diverse_ads(raw_storage)
        results = await raw_storage.explorer_query(limit=2)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_group_by_company_id(self, raw_storage):
        await _seed_diverse_ads(raw_storage)
        results = await raw_storage.explorer_query(group_by="company_id")
        # Should group — at least the ads with manufacturer_data have company_ids
        assert isinstance(results, list)
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_group_by_ad_type(self, raw_storage):
        await _seed_diverse_ads(raw_storage)
        results = await raw_storage.explorer_query(group_by="ad_type")
        assert isinstance(results, list)
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_derived_fields_company_id_int(self, raw_storage):
        """Results should include derived company_id_int from manufacturer_data_hex."""
        apple_ad = _make_ad("AA:BB:CC:DD:EE:01", manufacturer_data=b"\x4c\x00\x10\x05\x01")
        await raw_storage.save(apple_ad)
        results = await raw_storage.explorer_query()
        assert results[0]["company_id_int"] == 76  # 0x004C little-endian

    @pytest.mark.asyncio
    async def test_derived_fields_payload_hex(self, raw_storage):
        """Results should include payload_hex (manufacturer_data without company_id prefix)."""
        apple_ad = _make_ad("AA:BB:CC:DD:EE:01", manufacturer_data=b"\x4c\x00\x10\x05\x01")
        await raw_storage.save(apple_ad)
        results = await raw_storage.explorer_query()
        assert results[0]["payload_hex"] == "100501"

    @pytest.mark.asyncio
    async def test_derived_fields_payload_length(self, raw_storage):
        """Results should include payload_length."""
        apple_ad = _make_ad("AA:BB:CC:DD:EE:01", manufacturer_data=b"\x4c\x00\x10\x05\x01")
        await raw_storage.save(apple_ad)
        results = await raw_storage.explorer_query()
        # Full manufacturer_data is 5 bytes
        assert results[0]["payload_length"] == 5

    @pytest.mark.asyncio
    async def test_no_manufacturer_data_derived_fields(self, raw_storage):
        """Ads without manufacturer_data should have None for derived fields."""
        ad = _make_ad("11:22:33:44:55:66", local_name="SomeDevice")
        await raw_storage.save(ad)
        results = await raw_storage.explorer_query()
        assert results[0]["company_id_int"] is None
        assert results[0]["payload_hex"] is None


# ===================================================================
# get_by_id() tests
# ===================================================================

class TestGetById:
    @pytest.mark.asyncio
    async def test_returns_row_for_valid_id(self, raw_storage):
        ad = _make_ad("AA:BB:CC:DD:EE:01", manufacturer_data=b"\x4c\x00\x10\x05")
        await raw_storage.save(ad)
        row = await raw_storage.get_by_id(1)
        assert row is not None
        assert row["mac_address"] == "AA:BB:CC:DD:EE:01"

    @pytest.mark.asyncio
    async def test_returns_none_for_invalid_id(self, raw_storage):
        result = await raw_storage.get_by_id(9999)
        assert result is None


# ===================================================================
# get_facets() tests
# ===================================================================

class TestGetFacets:
    @pytest.mark.asyncio
    async def test_returns_ad_types_with_counts(self, raw_storage):
        await _seed_diverse_ads(raw_storage)
        facets = await raw_storage.get_facets()
        assert "ad_types" in facets
        ad_types = facets["ad_types"]
        assert isinstance(ad_types, list)
        assert len(ad_types) > 0
        # Each entry should have type and count
        entry = ad_types[0]
        assert "value" in entry
        assert "count" in entry

    @pytest.mark.asyncio
    async def test_returns_company_ids_with_counts(self, raw_storage):
        await _seed_diverse_ads(raw_storage)
        facets = await raw_storage.get_facets()
        assert "company_ids" in facets
        assert len(facets["company_ids"]) > 0

    @pytest.mark.asyncio
    async def test_returns_service_uuids(self, raw_storage):
        await _seed_diverse_ads(raw_storage)
        facets = await raw_storage.get_facets()
        assert "service_uuids" in facets

    @pytest.mark.asyncio
    async def test_returns_top_local_names(self, raw_storage):
        await _seed_diverse_ads(raw_storage)
        facets = await raw_storage.get_facets()
        assert "local_names" in facets
        assert len(facets["local_names"]) > 0

    @pytest.mark.asyncio
    async def test_empty_database(self, raw_storage):
        facets = await raw_storage.get_facets()
        assert facets["ad_types"] == []
        assert facets["company_ids"] == []
        assert facets["service_uuids"] == []
        assert facets["local_names"] == []


# ===================================================================
# compare_ads() tests
# ===================================================================

class TestCompareAds:
    @pytest.mark.asyncio
    async def test_byte_aligned_comparison(self, raw_storage):
        """Given IDs, returns byte-by-byte comparison."""
        ad1 = _make_ad("AA:BB:CC:DD:EE:01", manufacturer_data=b"\x4c\x00\x10\x05\x01")
        ad2 = _make_ad("AA:BB:CC:DD:EE:02", manufacturer_data=b"\x4c\x00\x10\x07\x02")
        await raw_storage.save(ad1)
        await raw_storage.save(ad2)

        result = await raw_storage.compare_ads([1, 2])
        assert isinstance(result, list)
        assert len(result) > 0
        # Each entry has offset, values, is_constant
        entry = result[0]
        assert "offset" in entry
        assert "values" in entry
        assert "is_constant" in entry

    @pytest.mark.asyncio
    async def test_detects_constant_bytes(self, raw_storage):
        """Bytes that are the same across all ads should be marked constant."""
        ad1 = _make_ad("AA:BB:CC:DD:EE:01", manufacturer_data=b"\x4c\x00\xAA")
        ad2 = _make_ad("AA:BB:CC:DD:EE:02", manufacturer_data=b"\x4c\x00\xBB")
        await raw_storage.save(ad1)
        await raw_storage.save(ad2)

        result = await raw_storage.compare_ads([1, 2])
        # First two bytes (company_id 0x4c00) are constant
        assert result[0]["is_constant"] is True  # 0x4c
        assert result[1]["is_constant"] is True  # 0x00
        # Third byte differs
        assert result[2]["is_constant"] is False

    @pytest.mark.asyncio
    async def test_detects_variable_bytes(self, raw_storage):
        ad1 = _make_ad("AA:BB:CC:DD:EE:01", manufacturer_data=b"\x4c\x00\x01")
        ad2 = _make_ad("AA:BB:CC:DD:EE:02", manufacturer_data=b"\x4c\x00\x02")
        await raw_storage.save(ad1)
        await raw_storage.save(ad2)

        result = await raw_storage.compare_ads([1, 2])
        variable = [r for r in result if not r["is_constant"]]
        assert len(variable) >= 1

    @pytest.mark.asyncio
    async def test_empty_for_invalid_ids(self, raw_storage):
        result = await raw_storage.compare_ads([9999, 8888])
        assert result == []
