"""Tests for Protocol Specs storage layer (SpecStorage)."""

import pytest
import pytest_asyncio

from adwatch.storage.base import Database
from adwatch.storage.migrations import run_migrations
from adwatch.storage.specs import SpecStorage


@pytest_asyncio.fixture
async def db():
    """In-memory SQLite database, migrated and ready."""
    database = Database()
    await database.connect(":memory:")
    await run_migrations(database)
    yield database
    await database.close()


@pytest_asyncio.fixture
async def spec_storage(db):
    return SpecStorage(db)


# ===================================================================
# create_spec / get_spec / list_specs
# ===================================================================

class TestCreateSpec:
    @pytest.mark.asyncio
    async def test_create_spec_returns_dict_with_id(self, spec_storage):
        spec = await spec_storage.create_spec("my_protocol")
        assert isinstance(spec, dict)
        assert "id" in spec
        assert spec["name"] == "my_protocol"

    @pytest.mark.asyncio
    async def test_create_spec_with_all_fields(self, spec_storage):
        spec = await spec_storage.create_spec(
            "apple_nearby",
            description="Apple Nearby Info",
            company_id=76,
            service_uuid=None,
            local_name_pattern=None,
            data_source="mfr",
        )
        assert spec["name"] == "apple_nearby"
        assert spec["description"] == "Apple Nearby Info"
        assert spec["company_id"] == 76
        assert spec["data_source"] == "mfr"

    @pytest.mark.asyncio
    async def test_create_spec_sets_timestamps(self, spec_storage):
        spec = await spec_storage.create_spec("proto1")
        assert "created_at" in spec
        assert "updated_at" in spec
        assert spec["created_at"] is not None
        assert spec["updated_at"] is not None

    @pytest.mark.asyncio
    async def test_create_spec_unique_name(self, spec_storage):
        await spec_storage.create_spec("unique_name")
        with pytest.raises(Exception):
            await spec_storage.create_spec("unique_name")


class TestGetSpec:
    @pytest.mark.asyncio
    async def test_get_spec_returns_spec_with_fields(self, spec_storage):
        spec = await spec_storage.create_spec("proto1")
        await spec_storage.add_field(spec["id"], "temperature", 0, 2, "uint16")
        result = await spec_storage.get_spec(spec["id"])
        assert result["name"] == "proto1"
        assert "fields" in result
        assert len(result["fields"]) == 1

    @pytest.mark.asyncio
    async def test_get_spec_returns_none_for_missing(self, spec_storage):
        result = await spec_storage.get_spec(9999)
        assert result is None


class TestListSpecs:
    @pytest.mark.asyncio
    async def test_list_specs_empty(self, spec_storage):
        specs = await spec_storage.list_specs()
        assert specs == []

    @pytest.mark.asyncio
    async def test_list_specs_returns_all(self, spec_storage):
        await spec_storage.create_spec("proto1")
        await spec_storage.create_spec("proto2")
        specs = await spec_storage.list_specs()
        assert len(specs) == 2

    @pytest.mark.asyncio
    async def test_list_specs_does_not_include_fields(self, spec_storage):
        spec = await spec_storage.create_spec("proto1")
        await spec_storage.add_field(spec["id"], "temp", 0, 2, "uint16")
        specs = await spec_storage.list_specs()
        assert "fields" not in specs[0]


# ===================================================================
# update_spec / delete_spec
# ===================================================================

class TestUpdateSpec:
    @pytest.mark.asyncio
    async def test_update_spec_changes_fields(self, spec_storage):
        spec = await spec_storage.create_spec("proto1", description="old")
        updated = await spec_storage.update_spec(spec["id"], description="new")
        assert updated["description"] == "new"

    @pytest.mark.asyncio
    async def test_update_spec_updates_timestamp(self, spec_storage):
        spec = await spec_storage.create_spec("proto1")
        original_updated_at = spec["updated_at"]
        updated = await spec_storage.update_spec(spec["id"], description="changed")
        assert updated["updated_at"] >= original_updated_at

    @pytest.mark.asyncio
    async def test_update_spec_returns_none_for_missing(self, spec_storage):
        result = await spec_storage.update_spec(9999, description="nope")
        assert result is None


class TestDeleteSpec:
    @pytest.mark.asyncio
    async def test_delete_spec(self, spec_storage):
        spec = await spec_storage.create_spec("proto1")
        await spec_storage.delete_spec(spec["id"])
        assert await spec_storage.get_spec(spec["id"]) is None

    @pytest.mark.asyncio
    async def test_delete_spec_cascades_fields(self, spec_storage):
        spec = await spec_storage.create_spec("proto1")
        await spec_storage.add_field(spec["id"], "temp", 0, 2, "uint16")
        await spec_storage.add_field(spec["id"], "humidity", 2, 1, "uint8")
        await spec_storage.delete_spec(spec["id"])
        fields = await spec_storage.get_fields(spec["id"])
        assert fields == []


# ===================================================================
# add_field / get_fields / update_field / delete_field
# ===================================================================

class TestAddField:
    @pytest.mark.asyncio
    async def test_add_field_returns_dict(self, spec_storage):
        spec = await spec_storage.create_spec("proto1")
        field = await spec_storage.add_field(spec["id"], "temperature", 0, 2, "uint16")
        assert isinstance(field, dict)
        assert "id" in field
        assert field["name"] == "temperature"
        assert field["offset"] == 0
        assert field["length"] == 2
        assert field["field_type"] == "uint16"

    @pytest.mark.asyncio
    async def test_add_field_default_endian(self, spec_storage):
        spec = await spec_storage.create_spec("proto1")
        field = await spec_storage.add_field(spec["id"], "temp", 0, 2, "uint16")
        assert field["endian"] == "LE"

    @pytest.mark.asyncio
    async def test_add_field_with_all_params(self, spec_storage):
        spec = await spec_storage.create_spec("proto1")
        field = await spec_storage.add_field(
            spec["id"], "temp", 0, 2, "int16",
            endian="BE", description="Temperature in C * 10", sort_order=5,
        )
        assert field["endian"] == "BE"
        assert field["description"] == "Temperature in C * 10"
        assert field["sort_order"] == 5

    @pytest.mark.asyncio
    async def test_add_field_unique_name_within_spec(self, spec_storage):
        spec = await spec_storage.create_spec("proto1")
        await spec_storage.add_field(spec["id"], "temp", 0, 2, "uint16")
        with pytest.raises(Exception):
            await spec_storage.add_field(spec["id"], "temp", 2, 2, "uint16")

    @pytest.mark.asyncio
    async def test_same_field_name_different_specs(self, spec_storage):
        """Field name uniqueness is per-spec, not global."""
        spec1 = await spec_storage.create_spec("proto1")
        spec2 = await spec_storage.create_spec("proto2")
        f1 = await spec_storage.add_field(spec1["id"], "temp", 0, 2, "uint16")
        f2 = await spec_storage.add_field(spec2["id"], "temp", 0, 2, "uint16")
        assert f1["id"] != f2["id"]


class TestGetFields:
    @pytest.mark.asyncio
    async def test_get_fields_ordered_by_sort_order_then_offset(self, spec_storage):
        spec = await spec_storage.create_spec("proto1")
        await spec_storage.add_field(spec["id"], "c_field", 4, 1, "uint8", sort_order=2)
        await spec_storage.add_field(spec["id"], "a_field", 0, 2, "uint16", sort_order=1)
        await spec_storage.add_field(spec["id"], "b_field", 2, 2, "uint16", sort_order=1)
        fields = await spec_storage.get_fields(spec["id"])
        assert len(fields) == 3
        # sort_order=1 first, then by offset: a_field(0), b_field(2), then sort_order=2: c_field(4)
        assert fields[0]["name"] == "a_field"
        assert fields[1]["name"] == "b_field"
        assert fields[2]["name"] == "c_field"

    @pytest.mark.asyncio
    async def test_get_fields_empty(self, spec_storage):
        spec = await spec_storage.create_spec("proto1")
        fields = await spec_storage.get_fields(spec["id"])
        assert fields == []


class TestUpdateField:
    @pytest.mark.asyncio
    async def test_update_field(self, spec_storage):
        spec = await spec_storage.create_spec("proto1")
        field = await spec_storage.add_field(spec["id"], "temp", 0, 2, "uint16")
        updated = await spec_storage.update_field(field["id"], name="temperature", endian="BE")
        assert updated["name"] == "temperature"
        assert updated["endian"] == "BE"

    @pytest.mark.asyncio
    async def test_update_field_returns_none_for_missing(self, spec_storage):
        result = await spec_storage.update_field(9999, name="nope")
        assert result is None


class TestDeleteField:
    @pytest.mark.asyncio
    async def test_delete_field(self, spec_storage):
        spec = await spec_storage.create_spec("proto1")
        field = await spec_storage.add_field(spec["id"], "temp", 0, 2, "uint16")
        await spec_storage.delete_field(field["id"])
        fields = await spec_storage.get_fields(spec["id"])
        assert fields == []


# ===================================================================
# match_specs
# ===================================================================

class TestMatchSpecs:
    @pytest.mark.asyncio
    async def test_match_by_company_id(self, spec_storage):
        """Match when company_id matches uint16 LE from first 4 hex chars of manufacturer_data_hex."""
        await spec_storage.create_spec("apple_proto", company_id=76)
        # 0x4c00 = 76 in LE
        ad_row = {"manufacturer_data_hex": "4c00100501", "service_uuids_json": "[]", "local_name": None}
        matches = await spec_storage.match_specs(ad_row)
        assert len(matches) == 1
        assert matches[0]["name"] == "apple_proto"

    @pytest.mark.asyncio
    async def test_match_by_service_uuid(self, spec_storage):
        await spec_storage.create_spec("fast_pair_proto", service_uuid="0000fe2c-0000-1000-8000-00805f9b34fb")
        ad_row = {
            "manufacturer_data_hex": None,
            "service_uuids_json": '["0000fe2c-0000-1000-8000-00805f9b34fb"]',
            "local_name": None,
        }
        matches = await spec_storage.match_specs(ad_row)
        assert len(matches) == 1
        assert matches[0]["name"] == "fast_pair_proto"

    @pytest.mark.asyncio
    async def test_match_by_local_name_pattern(self, spec_storage):
        await spec_storage.create_spec("thermo_proto", local_name_pattern=r"^TP\d+")
        ad_row = {"manufacturer_data_hex": None, "service_uuids_json": "[]", "local_name": "TP357 (2B54)"}
        matches = await spec_storage.match_specs(ad_row)
        assert len(matches) == 1

    @pytest.mark.asyncio
    async def test_match_or_logic(self, spec_storage):
        """Any single criterion matching is sufficient (OR logic)."""
        await spec_storage.create_spec(
            "multi_match",
            company_id=76,
            service_uuid="abcd",
            local_name_pattern=r"^TP\d+",
        )
        # Only company_id matches
        ad_row = {"manufacturer_data_hex": "4c00aabb", "service_uuids_json": "[]", "local_name": None}
        matches = await spec_storage.match_specs(ad_row)
        assert len(matches) == 1

    @pytest.mark.asyncio
    async def test_no_match(self, spec_storage):
        await spec_storage.create_spec("apple_proto", company_id=76)
        # Microsoft company_id = 6 (0x0600)
        ad_row = {"manufacturer_data_hex": "06000109", "service_uuids_json": "[]", "local_name": None}
        matches = await spec_storage.match_specs(ad_row)
        assert len(matches) == 0

    @pytest.mark.asyncio
    async def test_match_multiple_specs(self, spec_storage):
        """Multiple specs can match the same ad."""
        await spec_storage.create_spec("spec_a", company_id=76)
        await spec_storage.create_spec("spec_b", company_id=76)
        ad_row = {"manufacturer_data_hex": "4c001005", "service_uuids_json": "[]", "local_name": None}
        matches = await spec_storage.match_specs(ad_row)
        assert len(matches) == 2

    @pytest.mark.asyncio
    async def test_match_spec_with_no_criteria_does_not_match(self, spec_storage):
        """A spec with no match criteria should not match any ad."""
        await spec_storage.create_spec("empty_spec")
        ad_row = {"manufacturer_data_hex": "4c001005", "service_uuids_json": "[]", "local_name": None}
        matches = await spec_storage.match_specs(ad_row)
        assert len(matches) == 0

    @pytest.mark.asyncio
    async def test_match_with_null_manufacturer_data(self, spec_storage):
        """company_id match should not crash when manufacturer_data_hex is None."""
        await spec_storage.create_spec("apple_proto", company_id=76)
        ad_row = {"manufacturer_data_hex": None, "service_uuids_json": "[]", "local_name": None}
        matches = await spec_storage.match_specs(ad_row)
        assert len(matches) == 0

    @pytest.mark.asyncio
    async def test_match_with_short_manufacturer_data(self, spec_storage):
        """company_id match should not crash when manufacturer_data_hex is too short."""
        await spec_storage.create_spec("apple_proto", company_id=76)
        ad_row = {"manufacturer_data_hex": "4c", "service_uuids_json": "[]", "local_name": None}
        matches = await spec_storage.match_specs(ad_row)
        assert len(matches) == 0


# ===================================================================
# Name validation
# ===================================================================

class TestSpecNameValidation:
    @pytest.mark.asyncio
    async def test_rejects_name_with_spaces(self, spec_storage):
        with pytest.raises(ValueError):
            await spec_storage.create_spec("has space")

    @pytest.mark.asyncio
    async def test_rejects_name_with_quotes(self, spec_storage):
        with pytest.raises(ValueError):
            await spec_storage.create_spec('has"quote')

    @pytest.mark.asyncio
    async def test_rejects_empty_name(self, spec_storage):
        with pytest.raises(ValueError):
            await spec_storage.create_spec("")

    @pytest.mark.asyncio
    async def test_accepts_valid_name(self, spec_storage):
        spec = await spec_storage.create_spec("valid_Name_123")
        assert spec["name"] == "valid_Name_123"

    @pytest.mark.asyncio
    async def test_accepts_name_with_dashes(self, spec_storage):
        spec = await spec_storage.create_spec("my-protocol")
        assert spec["name"] == "my-protocol"

    @pytest.mark.asyncio
    async def test_accepts_name_with_dots(self, spec_storage):
        spec = await spec_storage.create_spec("v1.2_proto")
        assert spec["name"] == "v1.2_proto"

    @pytest.mark.asyncio
    async def test_rejects_name_starting_with_digit(self, spec_storage):
        with pytest.raises(ValueError):
            await spec_storage.create_spec("1bad")


class TestFieldNameValidation:
    @pytest.mark.asyncio
    async def test_rejects_field_name_with_spaces(self, spec_storage):
        spec = await spec_storage.create_spec("proto1")
        with pytest.raises(ValueError):
            await spec_storage.add_field(spec["id"], "bad name", 0, 2, "uint16")

    @pytest.mark.asyncio
    async def test_rejects_empty_field_name(self, spec_storage):
        spec = await spec_storage.create_spec("proto1")
        with pytest.raises(ValueError):
            await spec_storage.add_field(spec["id"], "", 0, 2, "uint16")
