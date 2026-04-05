"""Tests for InsightsAggregator."""

import json
import time

import pytest

from adwatch.storage.base import Database
from adwatch.storage.migrations import run_migrations
from adwatch.insights.aggregator import InsightsAggregator


@pytest.fixture
async def db():
    d = Database()
    await d.connect(":memory:")
    await run_migrations(d)
    yield d
    await d.close()


async def _insert_ad(db, **kwargs):
    """Insert a raw_advertisement row with defaults."""
    defaults = {
        "ad_signature": f"sig_{time.time()}_{id(kwargs)}",
        "first_seen": time.time() - 3600,
        "last_seen": time.time(),
        "sighting_count": 1,
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "address_type": "random",
        "manufacturer_data_hex": None,
        "service_data_json": None,
        "service_uuids_json": None,
        "local_name": None,
        "rssi_min": -80,
        "rssi_max": -60,
        "rssi_total": -70,
        "tx_power": None,
        "ad_type": None,
        "parsed_by": None,
    }
    defaults.update(kwargs)
    cols = ", ".join(defaults.keys())
    placeholders = ", ".join(["?"] * len(defaults))
    await db.execute(
        f"INSERT INTO raw_advertisements ({cols}) VALUES ({placeholders})",
        tuple(defaults.values()),
    )


class TestInsightsAggregator:
    async def test_build_summary_empty_db(self, db):
        agg = InsightsAggregator(db)
        summary = await agg.build_summary()
        assert summary["totals"]["total_ads"] == 0
        assert summary["totals"]["parsed"] == 0
        assert summary["totals"]["unparsed"] == 0

    async def test_totals(self, db):
        await _insert_ad(db, ad_signature="s1", parsed_by="hatch", ad_type="hatch")
        await _insert_ad(db, ad_signature="s2", parsed_by="sonos", ad_type="sonos")
        await _insert_ad(db, ad_signature="s3")  # unparsed

        agg = InsightsAggregator(db)
        summary = await agg.build_summary()
        assert summary["totals"]["total_ads"] == 3
        assert summary["totals"]["parsed"] == 2
        assert summary["totals"]["unparsed"] == 1

    async def test_parse_rate(self, db):
        await _insert_ad(db, ad_signature="s1", parsed_by="hatch", ad_type="hatch")
        await _insert_ad(db, ad_signature="s2")

        agg = InsightsAggregator(db)
        summary = await agg.build_summary()
        assert summary["totals"]["parse_rate"] == pytest.approx(0.5)

    async def test_by_parser(self, db):
        await _insert_ad(db, ad_signature="s1", parsed_by="hatch", ad_type="hatch", sighting_count=100)
        await _insert_ad(db, ad_signature="s2", parsed_by="hatch", ad_type="hatch", sighting_count=50)
        await _insert_ad(db, ad_signature="s3", parsed_by="sonos", ad_type="sonos", sighting_count=30)

        agg = InsightsAggregator(db)
        summary = await agg.build_summary()
        parsers = {p["parser"]: p for p in summary["by_parser"]}
        assert "hatch" in parsers
        assert parsers["hatch"]["count"] == 2
        assert parsers["hatch"]["sightings"] == 150

    async def test_top_devices(self, db):
        await _insert_ad(
            db, ad_signature="s1", local_name="Bedroom Hatch",
            parsed_by="hatch", ad_type="hatch", sighting_count=5000,
            mac_address="11:22:33:44:55:66",
        )
        await _insert_ad(
            db, ad_signature="s2", local_name="TP357S",
            parsed_by="thermopro", ad_type="thermopro", sighting_count=100,
            mac_address="AA:BB:CC:DD:EE:FF",
        )

        agg = InsightsAggregator(db)
        summary = await agg.build_summary()
        assert len(summary["top_devices"]) >= 2
        assert summary["top_devices"][0]["local_name"] == "Bedroom Hatch"
        assert summary["top_devices"][0]["sightings"] == 5000

    async def test_unparsed_named(self, db):
        await _insert_ad(
            db, ad_signature="s1", local_name="PLAUD_NOTE",
            sighting_count=72,
            service_uuids_json=None,
            manufacturer_data_hex="590002780304",
        )

        agg = InsightsAggregator(db)
        summary = await agg.build_summary()
        assert len(summary["unparsed_named"]) == 1
        assert summary["unparsed_named"][0]["local_name"] == "PLAUD_NOTE"

    async def test_scan_period(self, db):
        now = time.time()
        await _insert_ad(db, ad_signature="s1", first_seen=now - 7200, last_seen=now - 3600)
        await _insert_ad(db, ad_signature="s2", first_seen=now - 3600, last_seen=now)

        agg = InsightsAggregator(db)
        summary = await agg.build_summary()
        assert "scan_period" in summary
        assert summary["scan_period"]["duration_hours"] == pytest.approx(2.0, abs=0.1)

    async def test_summary_has_all_keys(self, db):
        await _insert_ad(db, ad_signature="s1", parsed_by="test", ad_type="test")

        agg = InsightsAggregator(db)
        summary = await agg.build_summary()
        expected_keys = {
            "scan_period", "totals", "by_parser", "by_device_class",
            "top_devices", "unparsed_named", "unparsed_uuid_freq",
            "unparsed_company_freq", "recent_new_devices_24h",
        }
        assert expected_keys.issubset(set(summary.keys()))

    async def test_no_mac_addresses_in_output(self, db):
        """Ensure no raw MAC addresses leak into the summary."""
        await _insert_ad(
            db, ad_signature="s1", mac_address="DE:AD:BE:EF:CA:FE",
            local_name="Test", parsed_by="test", ad_type="test",
            sighting_count=100,
        )

        agg = InsightsAggregator(db)
        summary = await agg.build_summary()
        summary_str = json.dumps(summary)
        assert "DE:AD:BE:EF:CA:FE" not in summary_str
