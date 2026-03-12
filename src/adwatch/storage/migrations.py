"""Schema creation and migration for adwatch."""

from adwatch.storage.base import Database


async def run_migrations(db: Database, registry=None) -> None:
    """Create tables and indexes. Idempotent."""
    await db.execute("""
        CREATE TABLE IF NOT EXISTS raw_advertisements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad_signature TEXT NOT NULL,
            first_seen REAL NOT NULL,
            last_seen REAL NOT NULL,
            sighting_count INTEGER DEFAULT 1,
            mac_address TEXT NOT NULL,
            address_type TEXT,
            manufacturer_data_hex TEXT,
            service_data_json TEXT,
            service_uuids_json TEXT,
            local_name TEXT,
            rssi_min INTEGER,
            rssi_max INTEGER,
            rssi_total INTEGER,
            tx_power INTEGER,
            ad_type TEXT,
            parsed_by TEXT,
            UNIQUE(ad_signature)
        )
    """)
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_raw_last_seen ON raw_advertisements(last_seen)"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_raw_mac ON raw_advertisements(mac_address)"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_raw_ad_type ON raw_advertisements(ad_type)"
    )

    await db.execute("""
        CREATE TABLE IF NOT EXISTS protocol_specs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            company_id INTEGER,
            service_uuid TEXT,
            local_name_pattern TEXT,
            data_source TEXT DEFAULT 'mfr',
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS protocol_spec_fields (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            spec_id INTEGER NOT NULL REFERENCES protocol_specs(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            offset INTEGER NOT NULL,
            length INTEGER NOT NULL,
            field_type TEXT NOT NULL,
            endian TEXT DEFAULT 'LE',
            description TEXT,
            sort_order INTEGER DEFAULT 0,
            UNIQUE(spec_id, name)
        )
    """)

    if registry:
        for p in registry.get_all():
            if hasattr(p.instance, "storage_schemas"):
                for schema in p.instance.storage_schemas():
                    await db.execute(schema)
            elif hasattr(p.instance, "storage_schema"):
                schema = p.instance.storage_schema()
                if schema:
                    await db.execute(schema)
