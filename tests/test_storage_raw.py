"""Tests for adwatch.storage.base, adwatch.storage.migrations, and adwatch.storage.raw."""

import hashlib
import json
import time

import pytest
import pytest_asyncio

from adwatch.models import Classification, RawAdvertisement
from adwatch.storage.base import Database
from adwatch.storage.migrations import run_migrations
from adwatch.storage.raw import RawStorage


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db():
    """In-memory SQLite database, migrated and ready."""
    database = Database()
    await database.connect(":memory:")
    await run_migrations(database)
    yield database
    await database.close()


@pytest_asyncio.fixture
async def raw_storage(db):
    """RawStorage backed by the in-memory database."""
    return RawStorage(db)


def _make_ad(
    *,
    mac="AA:BB:CC:DD:EE:FF",
    timestamp="2025-01-15T10:30:00+00:00",
    address_type="random",
    manufacturer_data=b"\x4c\x00\x10\x05\x01",
    service_data=None,
    service_uuids=None,
    local_name=None,
    rssi=-62,
    tx_power=None,
) -> RawAdvertisement:
    return RawAdvertisement(
        timestamp=timestamp,
        mac_address=mac,
        address_type=address_type,
        manufacturer_data=manufacturer_data,
        service_data=service_data,
        service_uuids=service_uuids or [],
        local_name=local_name,
        rssi=rssi,
        tx_power=tx_power,
    )


def _compute_expected_signature(
    mac="AA:BB:CC:DD:EE:FF",
    address_type="random",
    mfg_hex="4c00100501",
    sd_json=None,
    su_json=None,
    local_name=None,
) -> str:
    """Compute the expected ad_signature the same way RawStorage should."""
    parts = f"{mac}|{address_type}|{mfg_hex}|{sd_json}|{su_json}|{local_name}"
    return hashlib.sha256(parts.encode()).hexdigest()


# ===========================================================================
# storage.base — Database class
# ===========================================================================


class TestDatabase:
    """Tests for Database connection management and query helpers."""

    @pytest.mark.asyncio
    async def test_connect_and_close(self):
        db = Database()
        await db.connect(":memory:")
        # Should be usable after connect
        result = await db.fetchone("SELECT 1 AS val")
        assert result is not None
        await db.close()

    @pytest.mark.asyncio
    async def test_execute_creates_table(self):
        db = Database()
        await db.connect(":memory:")
        await db.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT)")
        await db.execute("INSERT INTO t (name) VALUES (?)", ("hello",))
        row = await db.fetchone("SELECT name FROM t WHERE id = 1")
        assert row["name"] == "hello"
        await db.close()

    @pytest.mark.asyncio
    async def test_fetchall_returns_list(self):
        db = Database()
        await db.connect(":memory:")
        await db.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
        await db.execute("INSERT INTO t (v) VALUES (?)", ("a",))
        await db.execute("INSERT INTO t (v) VALUES (?)", ("b",))
        rows = await db.fetchall("SELECT v FROM t ORDER BY v")
        assert len(rows) == 2
        assert rows[0]["v"] == "a"
        assert rows[1]["v"] == "b"
        await db.close()

    @pytest.mark.asyncio
    async def test_fetchone_returns_none_when_empty(self):
        db = Database()
        await db.connect(":memory:")
        await db.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
        row = await db.fetchone("SELECT * FROM t WHERE id = 999")
        assert row is None
        await db.close()

    @pytest.mark.asyncio
    async def test_execute_with_params(self):
        db = Database()
        await db.connect(":memory:")
        await db.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v INTEGER)")
        await db.execute("INSERT INTO t (v) VALUES (?)", (42,))
        row = await db.fetchone("SELECT v FROM t")
        assert row["v"] == 42
        await db.close()


# ===========================================================================
# storage.migrations — run_migrations (NEW SCHEMA)
# ===========================================================================


class TestMigrations:
    """Tests for schema migration (table and index creation)."""

    @pytest.mark.asyncio
    async def test_schema_has_correct_columns(self):
        """New schema has ad_signature, first_seen, last_seen, sighting_count,
        rssi_min, rssi_max, rssi_total — NOT timestamp, ad_category, or rssi."""
        db = Database()
        await db.connect(":memory:")
        await run_migrations(db)

        rows = await db.fetchall("PRAGMA table_info(raw_advertisements)")
        col_names = {r["name"] for r in rows}

        # Must have new columns
        for col in ("ad_signature", "first_seen", "last_seen", "sighting_count",
                     "rssi_min", "rssi_max", "rssi_total"):
            assert col in col_names, f"Missing new column: {col}"

        # Must NOT have old columns
        for col in ("timestamp", "ad_category", "rssi"):
            assert col not in col_names, f"Old column still present: {col}"

        await db.close()

    @pytest.mark.asyncio
    async def test_creates_correct_indexes(self):
        """Creates idx_raw_last_seen, idx_raw_mac, idx_raw_ad_type (NOT idx_raw_timestamp)."""
        db = Database()
        await db.connect(":memory:")
        await run_migrations(db)

        rows = await db.fetchall(
            "SELECT name FROM sqlite_master WHERE type = 'index' AND tbl_name = 'raw_advertisements'"
        )
        index_names = {r["name"] for r in rows}
        assert "idx_raw_last_seen" in index_names
        assert "idx_raw_mac" in index_names
        assert "idx_raw_ad_type" in index_names
        assert "idx_raw_timestamp" not in index_names
        await db.close()

    @pytest.mark.asyncio
    async def test_ad_signature_unique_constraint(self):
        """ad_signature column has a UNIQUE constraint."""
        db = Database()
        await db.connect(":memory:")
        await run_migrations(db)

        # Insert two rows with the same ad_signature — should fail
        now = time.time()
        await db.execute(
            "INSERT INTO raw_advertisements (ad_signature, first_seen, last_seen, mac_address) "
            "VALUES (?, ?, ?, ?)",
            ("sig123", now, now, "AA:BB:CC:DD:EE:FF"),
        )
        with pytest.raises(Exception):
            await db.execute(
                "INSERT INTO raw_advertisements (ad_signature, first_seen, last_seen, mac_address) "
                "VALUES (?, ?, ?, ?)",
                ("sig123", now, now, "AA:BB:CC:DD:EE:FF"),
            )
        await db.close()

    @pytest.mark.asyncio
    async def test_migrations_idempotent(self):
        """Running migrations twice should not raise."""
        db = Database()
        await db.connect(":memory:")
        await run_migrations(db)
        await run_migrations(db)  # Second run must not fail
        row = await db.fetchone("SELECT count(*) AS cnt FROM raw_advertisements")
        assert row["cnt"] == 0
        await db.close()


# ===========================================================================
# storage.raw — RawStorage.save (dedup / upsert)
# ===========================================================================


class TestRawStorageSave:
    """Tests for saving raw advertisements with deduplication."""

    @pytest.mark.asyncio
    async def test_save_computes_ad_signature(self, raw_storage, db):
        """save() computes ad_signature as SHA256 of content fields."""
        ad = _make_ad()
        await raw_storage.save(ad)

        row = await db.fetchone("SELECT ad_signature FROM raw_advertisements")
        assert row is not None
        assert row["ad_signature"] is not None
        # Signature should be a hex SHA256
        assert len(row["ad_signature"]) == 64

    @pytest.mark.asyncio
    async def test_save_signature_matches_expected(self, raw_storage, db):
        """Signature is SHA256 of (mac, address_type, mfg_hex, sd_json, su_json, local_name)."""
        ad = _make_ad()
        await raw_storage.save(ad)

        row = await db.fetchone("SELECT ad_signature FROM raw_advertisements")
        expected = _compute_expected_signature()
        assert row["ad_signature"] == expected

    @pytest.mark.asyncio
    async def test_save_stores_unix_timestamps(self, raw_storage, db):
        """first_seen and last_seen are stored as REAL unix timestamps."""
        ad = _make_ad()
        await raw_storage.save(ad)

        row = await db.fetchone("SELECT first_seen, last_seen FROM raw_advertisements")
        assert isinstance(row["first_seen"], float)
        assert isinstance(row["last_seen"], float)
        assert row["first_seen"] == row["last_seen"]
        # Should be a reasonable unix timestamp (after 2020)
        assert row["first_seen"] > 1577836800  # 2020-01-01

    @pytest.mark.asyncio
    async def test_save_stores_rssi_as_min_max_total(self, raw_storage, db):
        """First save stores rssi as rssi_min, rssi_max, and rssi_total (all equal)."""
        ad = _make_ad(rssi=-62)
        await raw_storage.save(ad)

        row = await db.fetchone(
            "SELECT rssi_min, rssi_max, rssi_total FROM raw_advertisements"
        )
        assert row["rssi_min"] == -62
        assert row["rssi_max"] == -62
        assert row["rssi_total"] == -62

    @pytest.mark.asyncio
    async def test_save_stores_sighting_count_1(self, raw_storage, db):
        """First insert has sighting_count = 1."""
        ad = _make_ad()
        await raw_storage.save(ad)

        row = await db.fetchone("SELECT sighting_count FROM raw_advertisements")
        assert row["sighting_count"] == 1

    @pytest.mark.asyncio
    async def test_duplicate_save_upserts(self, raw_storage, db):
        """Saving the same ad twice does upsert: bumps count, updates last_seen, updates rssi."""
        ad1 = _make_ad(rssi=-62)
        ad2 = _make_ad(rssi=-70)  # Same content, different rssi

        await raw_storage.save(ad1)
        await raw_storage.save(ad2)

        row = await db.fetchone(
            "SELECT sighting_count, rssi_min, rssi_max, rssi_total, first_seen, last_seen "
            "FROM raw_advertisements"
        )
        # Only one row (deduped)
        count = await db.fetchone("SELECT count(*) AS cnt FROM raw_advertisements")
        assert count["cnt"] == 1

        assert row["sighting_count"] == 2
        assert row["rssi_min"] == -70  # min of -62, -70
        assert row["rssi_max"] == -62  # max of -62, -70
        assert row["rssi_total"] == -62 + -70  # sum
        assert row["last_seen"] >= row["first_seen"]

    @pytest.mark.asyncio
    async def test_save_classification_stores_ad_type_not_ad_category(self, raw_storage, db):
        """save() with classification stores ad_type but NOT ad_category (column doesn't exist)."""
        ad = _make_ad()
        classification = Classification(
            ad_type="apple_nearby",
            ad_category="phone",
            source="company_id",
        )
        await raw_storage.save(ad, classification=classification)

        row = await db.fetchone("SELECT ad_type FROM raw_advertisements")
        assert row["ad_type"] == "apple_nearby"

        # ad_category column should not exist
        cols = await db.fetchall("PRAGMA table_info(raw_advertisements)")
        col_names = {r["name"] for r in cols}
        assert "ad_category" not in col_names

    @pytest.mark.asyncio
    async def test_upsert_updates_ad_type_when_initially_null(self, raw_storage, db):
        """If an ad was first stored without classification, later upserts should fill ad_type."""
        ad = _make_ad()
        # First save: no classification
        await raw_storage.save(ad)
        row = await db.fetchone("SELECT ad_type FROM raw_advertisements")
        assert row["ad_type"] is None

        # Second save: with classification
        classification = Classification(
            ad_type="apple_nearby",
            ad_category="phone",
            source="company_id",
        )
        await raw_storage.save(ad, classification=classification)
        row = await db.fetchone("SELECT ad_type FROM raw_advertisements")
        assert row["ad_type"] == "apple_nearby"

    @pytest.mark.asyncio
    async def test_upsert_does_not_clear_existing_ad_type(self, raw_storage, db):
        """If ad_type is already set, a subsequent save without classification should not clear it."""
        ad = _make_ad()
        classification = Classification(
            ad_type="apple_nearby",
            ad_category="phone",
            source="company_id",
        )
        await raw_storage.save(ad, classification=classification)

        # Second save: no classification
        await raw_storage.save(ad)
        row = await db.fetchone("SELECT ad_type FROM raw_advertisements")
        assert row["ad_type"] == "apple_nearby"

    @pytest.mark.asyncio
    async def test_save_with_parsed_by(self, raw_storage, db):
        """parsed_by stores comma-separated string."""
        ad = _make_ad()
        await raw_storage.save(ad, parsed_by=["apple_continuity", "apple_findmy"])

        row = await db.fetchone("SELECT parsed_by FROM raw_advertisements")
        assert row["parsed_by"] == "apple_continuity,apple_findmy"

    @pytest.mark.asyncio
    async def test_save_stores_manufacturer_data_as_hex(self, raw_storage, db):
        ad = _make_ad(manufacturer_data=b"\x4c\x00\xAB\xCD")
        await raw_storage.save(ad)

        row = await db.fetchone("SELECT manufacturer_data_hex FROM raw_advertisements")
        assert row["manufacturer_data_hex"] == "4c00abcd"

    @pytest.mark.asyncio
    async def test_save_stores_service_data_as_json(self, raw_storage, db):
        sd = {"0000fe2c-0000-1000-8000-00805f9b34fb": b"\xAA\xBB"}
        ad = _make_ad(manufacturer_data=None, service_data=sd)
        await raw_storage.save(ad)

        row = await db.fetchone("SELECT service_data_json FROM raw_advertisements")
        parsed = json.loads(row["service_data_json"])
        assert "0000fe2c-0000-1000-8000-00805f9b34fb" in parsed

    @pytest.mark.asyncio
    async def test_save_stores_service_uuids_as_json(self, raw_storage, db):
        ad = _make_ad(service_uuids=["0000fe2c-0000-1000-8000-00805f9b34fb", "abcd"])
        await raw_storage.save(ad)

        row = await db.fetchone("SELECT service_uuids_json FROM raw_advertisements")
        parsed = json.loads(row["service_uuids_json"])
        assert len(parsed) == 2

    @pytest.mark.asyncio
    async def test_save_null_manufacturer_data(self, raw_storage, db):
        ad = _make_ad(manufacturer_data=None)
        await raw_storage.save(ad)

        row = await db.fetchone("SELECT manufacturer_data_hex FROM raw_advertisements")
        assert row["manufacturer_data_hex"] is None

    @pytest.mark.asyncio
    async def test_save_with_local_name(self, raw_storage, db):
        ad = _make_ad(local_name="TP357 (2B54)")
        await raw_storage.save(ad)

        row = await db.fetchone("SELECT local_name FROM raw_advertisements")
        assert row["local_name"] == "TP357 (2B54)"

    @pytest.mark.asyncio
    async def test_save_with_tx_power(self, raw_storage, db):
        ad = _make_ad(tx_power=4)
        await raw_storage.save(ad)

        row = await db.fetchone("SELECT tx_power FROM raw_advertisements")
        assert row["tx_power"] == 4

    @pytest.mark.asyncio
    async def test_save_different_macs_creates_multiple_rows(self, raw_storage, db):
        """Different content = different signatures = separate rows."""
        for i in range(5):
            ad = _make_ad(mac=f"AA:BB:CC:DD:EE:{i:02X}")
            await raw_storage.save(ad)

        row = await db.fetchone("SELECT count(*) AS cnt FROM raw_advertisements")
        assert row["cnt"] == 5

    @pytest.mark.asyncio
    async def test_save_without_classification_leaves_ad_type_null(self, raw_storage, db):
        ad = _make_ad()
        await raw_storage.save(ad)

        row = await db.fetchone("SELECT ad_type FROM raw_advertisements")
        assert row["ad_type"] is None


# ===========================================================================
# storage.raw — RawStorage.query
# ===========================================================================


class TestRawStorageQuery:
    """Tests for querying raw advertisements with filters."""

    @pytest.mark.asyncio
    async def test_query_results_include_timestamp_key(self, raw_storage):
        """query() results include `timestamp` key (alias for last_seen) for API compat."""
        await raw_storage.save(_make_ad())
        results = await raw_storage.query()
        assert len(results) == 1
        assert "timestamp" in results[0]

    @pytest.mark.asyncio
    async def test_query_since_uses_unix_timestamp(self, raw_storage):
        """query(since=...) filters by last_seen using unix timestamp comparison."""
        # Save ads with different macs (different signatures)
        ad1 = _make_ad(mac="AA:BB:CC:DD:EE:01")
        ad2 = _make_ad(mac="AA:BB:CC:DD:EE:02")
        ad3 = _make_ad(mac="AA:BB:CC:DD:EE:03")

        await raw_storage.save(ad1)
        await raw_storage.save(ad2)
        await raw_storage.save(ad3)

        # All should have similar last_seen timestamps (just now)
        # Query with since=0 should get all
        results = await raw_storage.query(since=0.0)
        assert len(results) == 3

        # Query with since=far future should get none
        results = await raw_storage.query(since=9999999999.0)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_query_by_mac(self, raw_storage):
        await raw_storage.save(_make_ad(mac="AA:BB:CC:DD:EE:01"))
        await raw_storage.save(_make_ad(mac="AA:BB:CC:DD:EE:02"))

        results = await raw_storage.query(mac="AA:BB:CC:DD:EE:01")
        assert len(results) == 1
        assert results[0]["mac_address"] == "AA:BB:CC:DD:EE:01"

    @pytest.mark.asyncio
    async def test_query_by_ad_type(self, raw_storage):
        cls_apple = Classification(ad_type="apple_nearby", ad_category="phone", source="company_id")
        cls_thermo = Classification(ad_type="thermopro", ad_category="sensor", source="local_name")

        await raw_storage.save(_make_ad(mac="AA:BB:CC:DD:EE:01"), classification=cls_apple)
        await raw_storage.save(
            _make_ad(mac="AA:BB:CC:DD:EE:02", manufacturer_data=None, local_name="TP357"),
            classification=cls_thermo,
        )

        results = await raw_storage.query(ad_type="apple_nearby")
        assert len(results) == 1
        assert results[0]["ad_type"] == "apple_nearby"

    @pytest.mark.asyncio
    async def test_query_with_limit(self, raw_storage):
        for i in range(10):
            await raw_storage.save(_make_ad(mac=f"AA:BB:CC:DD:EE:{i:02X}"))

        results = await raw_storage.query(limit=3)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_query_combined_filters(self, raw_storage):
        """Multiple filters combine (AND logic)."""
        cls_apple = Classification(ad_type="apple_nearby", ad_category="phone", source="company_id")

        await raw_storage.save(
            _make_ad(mac="AA:BB:CC:DD:EE:01"),
            classification=cls_apple,
        )
        await raw_storage.save(
            _make_ad(mac="AA:BB:CC:DD:EE:02"),
            classification=cls_apple,
        )

        results = await raw_storage.query(
            mac="AA:BB:CC:DD:EE:01",
            ad_type="apple_nearby",
        )
        assert len(results) == 1
        assert results[0]["mac_address"] == "AA:BB:CC:DD:EE:01"

    @pytest.mark.asyncio
    async def test_query_no_results(self, raw_storage):
        await raw_storage.save(_make_ad())
        results = await raw_storage.query(mac="FF:FF:FF:FF:FF:FF")
        assert results == []


# ===========================================================================
# storage.raw — RawStorage.get_feed
# ===========================================================================


class TestRawStorageGetFeed:
    """Tests for the live feed endpoint."""

    @pytest.mark.asyncio
    async def test_get_feed_ordered_by_last_seen_desc(self, raw_storage):
        """Feed results are ordered by last_seen DESC."""
        # Save 3 different ads
        await raw_storage.save(_make_ad(mac="AA:BB:CC:DD:EE:01"))
        await raw_storage.save(_make_ad(mac="AA:BB:CC:DD:EE:02"))
        await raw_storage.save(_make_ad(mac="AA:BB:CC:DD:EE:03"))

        results = await raw_storage.get_feed()
        assert len(results) == 3
        # last inserted should be first (most recent last_seen)
        assert results[0]["mac_address"] == "AA:BB:CC:DD:EE:03"

    @pytest.mark.asyncio
    async def test_get_feed_results_include_timestamp_key(self, raw_storage):
        """Feed results include `timestamp` key (alias for last_seen)."""
        await raw_storage.save(_make_ad())
        results = await raw_storage.get_feed()
        assert "timestamp" in results[0]

    @pytest.mark.asyncio
    async def test_get_feed_respects_limit(self, raw_storage):
        for i in range(10):
            await raw_storage.save(_make_ad(mac=f"AA:BB:CC:DD:EE:{i:02X}"))

        results = await raw_storage.get_feed(limit=5)
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_get_feed_empty_database(self, raw_storage):
        results = await raw_storage.get_feed()
        assert results == []


# ===========================================================================
# storage.raw — RawStorage.get_overview
# ===========================================================================


class TestRawStorageGetOverview:
    """Tests for the overview summary endpoint."""

    @pytest.mark.asyncio
    async def test_get_overview_groups_by_ad_type(self, raw_storage):
        """Overview groups by ad_type (NOT ad_category)."""
        cls_apple = Classification(ad_type="apple_nearby", ad_category="phone", source="company_id")
        cls_thermo = Classification(ad_type="thermopro", ad_category="sensor", source="local_name")

        await raw_storage.save(_make_ad(mac="AA:BB:CC:DD:EE:01"), classification=cls_apple)
        await raw_storage.save(_make_ad(mac="AA:BB:CC:DD:EE:02"), classification=cls_apple)
        await raw_storage.save(
            _make_ad(mac="AA:BB:CC:DD:EE:03", manufacturer_data=None, local_name="TP357"),
            classification=cls_thermo,
        )

        overview = await raw_storage.get_overview()
        assert isinstance(overview, dict)
        # Keys are ad_type values, not ad_category
        assert "apple_nearby" in overview
        assert "thermopro" in overview
        # Should NOT have ad_category keys
        assert "phone" not in overview
        assert "sensor" not in overview

    @pytest.mark.asyncio
    async def test_get_overview_includes_total_sightings(self, raw_storage):
        """Overview includes total_sightings (sum of sighting_count)."""
        cls_apple = Classification(ad_type="apple_nearby", ad_category="phone", source="company_id")

        # Save same ad twice (will dedup to sighting_count=2)
        ad = _make_ad()
        await raw_storage.save(ad, classification=cls_apple)
        await raw_storage.save(ad, classification=cls_apple)

        overview = await raw_storage.get_overview()
        # The overview for "apple_nearby" should reflect total_sightings
        assert "apple_nearby" in overview
        info = overview["apple_nearby"]
        # Should have total_sightings key (or be structured to include it)
        assert isinstance(info, dict)
        assert info["total_sightings"] == 2

    @pytest.mark.asyncio
    async def test_get_overview_empty_database(self, raw_storage):
        overview = await raw_storage.get_overview()
        assert isinstance(overview, dict)
        assert len(overview) == 0

    @pytest.mark.asyncio
    async def test_get_overview_excludes_null_ad_type(self, raw_storage):
        """Ads with no classification (ad_type=NULL) should not appear."""
        await raw_storage.save(_make_ad())  # No classification
        cls_apple = Classification(ad_type="apple_nearby", ad_category="phone", source="company_id")
        await raw_storage.save(_make_ad(mac="AA:BB:CC:DD:EE:02"), classification=cls_apple)

        overview = await raw_storage.get_overview()
        assert "apple_nearby" in overview
        assert len(overview) == 1  # only the one with ad_type


# ===========================================================================
# storage.raw — RawStorage.cleanup
# ===========================================================================


class TestRawStorageCleanup:
    """Tests for retention-based cleanup."""

    @pytest.mark.asyncio
    async def test_cleanup_deletes_by_last_seen(self, raw_storage, db):
        """cleanup() deletes by last_seen (unix timestamp comparison)."""
        # Insert a row with very old last_seen directly
        old_time = 1577836800.0  # 2020-01-01
        await db.execute(
            "INSERT INTO raw_advertisements (ad_signature, first_seen, last_seen, mac_address, sighting_count) "
            "VALUES (?, ?, ?, ?, ?)",
            ("old_sig", old_time, old_time, "OLD:OLD:OLD:OLD:OLD:01", 10),
        )

        # Insert a recent one via save
        await raw_storage.save(_make_ad(mac="NEW:NEW:NEW:NEW:NEW:01"))

        await raw_storage.cleanup(retention_days=1)

        # Old one should be gone
        results = await raw_storage.query(mac="OLD:OLD:OLD:OLD:OLD:01")
        assert len(results) == 0
        # New one should remain
        results = await raw_storage.query(mac="NEW:NEW:NEW:NEW:NEW:01")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_cleanup_sighting_count_threshold(self, raw_storage, db):
        """cleanup() has sighting_count threshold — protects rare ads (sighting_count <= threshold)."""
        old_time = 1577836800.0  # 2020-01-01

        # Rare ad: sighting_count=1 (should be PROTECTED by threshold)
        await db.execute(
            "INSERT INTO raw_advertisements (ad_signature, first_seen, last_seen, mac_address, sighting_count) "
            "VALUES (?, ?, ?, ?, ?)",
            ("rare_sig", old_time, old_time, "RARE:00:00:00:00:01", 1),
        )

        # Common ad: sighting_count=100 (should be DELETED)
        await db.execute(
            "INSERT INTO raw_advertisements (ad_signature, first_seen, last_seen, mac_address, sighting_count) "
            "VALUES (?, ?, ?, ?, ?)",
            ("common_sig", old_time, old_time, "COMMON:00:00:00:01", 100),
        )

        # cleanup with threshold=2 (protect ads with sighting_count <= 2)
        await raw_storage.cleanup(retention_days=1, sighting_count_threshold=2)

        # Rare ad should be kept (protected)
        results = await raw_storage.query(mac="RARE:00:00:00:00:01")
        assert len(results) == 1

        # Common ad should be deleted
        results = await raw_storage.query(mac="COMMON:00:00:00:01")
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_cleanup_zero_retention_removes_except_rare(self, raw_storage, db):
        """retention_days=0 removes everything except rare ads."""
        # Save a regular ad (sighting_count will be 1 via save, but then
        # we bump it to make it "common")
        await raw_storage.save(_make_ad(mac="AA:BB:CC:DD:EE:01"))
        # Manually bump sighting_count to make it common
        await db.execute(
            "UPDATE raw_advertisements SET sighting_count = 50 WHERE mac_address = ?",
            ("AA:BB:CC:DD:EE:01",),
        )

        # Save a rare ad (sighting_count=1)
        await raw_storage.save(_make_ad(mac="AA:BB:CC:DD:EE:02"))

        await raw_storage.cleanup(retention_days=0)

        # Common ad removed, rare ad kept
        row = await db.fetchone("SELECT count(*) AS cnt FROM raw_advertisements")
        assert row["cnt"] == 1
        remaining = await raw_storage.query(mac="AA:BB:CC:DD:EE:02")
        assert len(remaining) == 1


# ===========================================================================
# Integration: dedup lifecycle
# ===========================================================================


class TestRawStorageIntegration:
    """End-to-end tests combining save, query, feed, overview, and cleanup."""

    @pytest.mark.asyncio
    async def test_full_dedup_lifecycle(self, raw_storage, db):
        """Save same ad twice, verify single row with sighting_count=2."""
        cls_apple = Classification(ad_type="apple_nearby", ad_category="phone", source="company_id")

        ad = _make_ad(rssi=-55)
        await raw_storage.save(ad, classification=cls_apple, parsed_by=["apple_continuity"])

        # Same content, different rssi
        ad2 = _make_ad(rssi=-70)
        await raw_storage.save(ad2, classification=cls_apple, parsed_by=["apple_continuity"])

        # Should be ONE row
        count = await db.fetchone("SELECT count(*) AS cnt FROM raw_advertisements")
        assert count["cnt"] == 1

        # sighting_count should be 2
        row = await db.fetchone("SELECT sighting_count, rssi_min, rssi_max FROM raw_advertisements")
        assert row["sighting_count"] == 2
        assert row["rssi_min"] == -70
        assert row["rssi_max"] == -55

        # Feed should return 1 result with timestamp alias
        feed = await raw_storage.get_feed()
        assert len(feed) == 1
        assert "timestamp" in feed[0]

        # Query by mac should return 1
        results = await raw_storage.query(mac="AA:BB:CC:DD:EE:FF")
        assert len(results) == 1

        # Overview should group by ad_type
        overview = await raw_storage.get_overview()
        assert "apple_nearby" in overview

    @pytest.mark.asyncio
    async def test_save_with_all_fields(self, raw_storage):
        """Saving an ad with every field populated works correctly."""
        ad = RawAdvertisement(
            timestamp="2025-01-15T10:30:00+00:00",
            mac_address="AA:BB:CC:DD:EE:FF",
            address_type="public",
            manufacturer_data=b"\x4c\x00\x10\x05\x01\x18\x44\x00\x00",
            service_data={"abcd": b"\x01\x02"},
            service_uuids=["abcd", "1234"],
            local_name="TestDevice",
            rssi=-55,
            tx_power=8,
        )
        classification = Classification(
            ad_type="apple_nearby",
            ad_category="phone",
            source="company_id",
        )
        await raw_storage.save(ad, classification=classification, parsed_by=["apple_continuity"])

        results = await raw_storage.query(mac="AA:BB:CC:DD:EE:FF")
        assert len(results) == 1
        row = results[0]
        assert row["address_type"] == "public"
        assert row["local_name"] == "TestDevice"
        assert row["tx_power"] == 8
        assert row["ad_type"] == "apple_nearby"
        assert row["parsed_by"] == "apple_continuity"
        # New schema: rssi split into min/max/total
        assert row["rssi_min"] == -55
        assert row["rssi_max"] == -55
        assert row["rssi_total"] == -55
