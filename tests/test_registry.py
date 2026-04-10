"""Tests for adwatch.registry — Plugin Registry and @register_parser decorator."""

import pytest
from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser


# ---------------------------------------------------------------------------
# Stub parser classes used across tests
# ---------------------------------------------------------------------------

class _BaseStub:
    """Minimal parser interface that returns None for everything."""
    def parse(self, raw):
        return None

    def storage_schema(self):
        return None

    def api_router(self):
        return None

    def ui_config(self):
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ad(**kwargs):
    """Shortcut to build a RawAdvertisement with sensible defaults."""
    defaults = dict(
        timestamp="2025-01-15T10:30:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        manufacturer_data=None,
        service_data=None,
        service_uuids=[],
        local_name=None,
        rssi=-60,
        tx_power=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(**defaults)


# ===================================================================
# 1. Register a parser by company_id, verify it matches
# ===================================================================

class TestMatchByCompanyId:
    def test_matches_advertisement_with_matching_company_id(self):
        registry = ParserRegistry()

        @register_parser(
            name="test_company",
            company_id=0x004C,
            description="Test company parser",
            version="1.0.0",
            core=True,
            registry=registry,
        )
        class CompanyParser(_BaseStub):
            pass

        # manufacturer_data with company_id 0x004C (little-endian: 4c 00)
        ad = _make_ad(manufacturer_data=b"\x4c\x00\x10\x05\x01")
        matches = registry.match(ad)

        assert len(matches) == 1
        assert isinstance(matches[0], CompanyParser)

    def test_does_not_match_different_company_id(self):
        registry = ParserRegistry()

        @register_parser(
            name="test_company_miss",
            company_id=0x004C,
            description="Apple parser",
            version="1.0.0",
            core=True,
            registry=registry,
        )
        class AppleParser(_BaseStub):
            pass

        # company_id 0x0006 (Microsoft)
        ad = _make_ad(manufacturer_data=b"\x06\x00\x01\x02")
        matches = registry.match(ad)

        assert len(matches) == 0


# ===================================================================
# 2. Register a parser by service_uuid, verify it matches
# ===================================================================

class TestMatchByServiceUuid:
    def test_matches_advertisement_with_service_uuid_in_uuids_list(self):
        registry = ParserRegistry()

        @register_parser(
            name="test_uuid",
            service_uuid="0000fe2c-0000-1000-8000-00805f9b34fb",
            description="Fast Pair parser",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class UuidParser(_BaseStub):
            pass

        ad = _make_ad(
            service_uuids=["0000fe2c-0000-1000-8000-00805f9b34fb"],
        )
        matches = registry.match(ad)

        assert len(matches) == 1
        assert isinstance(matches[0], UuidParser)

    def test_matches_advertisement_with_service_uuid_in_service_data(self):
        registry = ParserRegistry()

        @register_parser(
            name="test_uuid_data",
            service_uuid="0000fe2c-0000-1000-8000-00805f9b34fb",
            description="Fast Pair parser (service_data)",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class UuidDataParser(_BaseStub):
            pass

        ad = _make_ad(
            service_data={"0000fe2c-0000-1000-8000-00805f9b34fb": b"\xAA\xBB"},
        )
        matches = registry.match(ad)

        assert len(matches) == 1
        assert isinstance(matches[0], UuidDataParser)

    def test_does_not_match_different_service_uuid(self):
        registry = ParserRegistry()

        @register_parser(
            name="test_uuid_miss",
            service_uuid="0000fe2c-0000-1000-8000-00805f9b34fb",
            description="Fast Pair only",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class UuidMissParser(_BaseStub):
            pass

        ad = _make_ad(
            service_uuids=["0000fff6-0000-1000-8000-00805f9b34fb"],
        )
        matches = registry.match(ad)

        assert len(matches) == 0


# ===================================================================
# 3. Register a parser by local_name_pattern (regex), verify it matches
# ===================================================================

class TestMatchByLocalNamePattern:
    def test_matches_local_name_regex(self):
        registry = ParserRegistry()

        @register_parser(
            name="test_name",
            local_name_pattern=r"^TP\d{3}",
            description="ThermoPro pattern",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class NameParser(_BaseStub):
            pass

        ad = _make_ad(local_name="TP357 (2B54)")
        matches = registry.match(ad)

        assert len(matches) == 1
        assert isinstance(matches[0], NameParser)

    def test_does_not_match_non_matching_name(self):
        registry = ParserRegistry()

        @register_parser(
            name="test_name_miss",
            local_name_pattern=r"^TP\d{3}",
            description="ThermoPro only",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class NameMissParser(_BaseStub):
            pass

        ad = _make_ad(local_name="SomeOtherDevice")
        matches = registry.match(ad)

        assert len(matches) == 0

    def test_does_not_match_none_local_name(self):
        registry = ParserRegistry()

        @register_parser(
            name="test_name_none",
            local_name_pattern=r"^TP\d{3}",
            description="ThermoPro only",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class NameNoneParser(_BaseStub):
            pass

        ad = _make_ad(local_name=None)
        matches = registry.match(ad)

        assert len(matches) == 0


# ===================================================================
# 4. Multiple criteria (OR logic)
# ===================================================================

class TestMultipleCriteriaOrLogic:
    def test_matches_on_company_id_alone(self):
        registry = ParserRegistry()

        @register_parser(
            name="test_or_company",
            company_id=0x00C2,
            local_name_pattern=r"^TP\d{3}",
            description="ThermoPro with OR",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class OrParser(_BaseStub):
            pass

        # Matches company_id but no local_name
        ad = _make_ad(manufacturer_data=b"\xC2\x00\x01\x02")
        matches = registry.match(ad)

        assert len(matches) == 1
        assert isinstance(matches[0], OrParser)

    def test_matches_on_local_name_alone(self):
        registry = ParserRegistry()

        @register_parser(
            name="test_or_name",
            company_id=0x00C2,
            local_name_pattern=r"^TP\d{3}",
            description="ThermoPro with OR",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class OrParser2(_BaseStub):
            pass

        # Matches local_name but no manufacturer_data
        ad = _make_ad(local_name="TP393 (1A2B)")
        matches = registry.match(ad)

        assert len(matches) == 1
        assert isinstance(matches[0], OrParser2)

    def test_matches_when_both_criteria_match(self):
        registry = ParserRegistry()

        @register_parser(
            name="test_or_both",
            company_id=0x00C2,
            local_name_pattern=r"^TP\d{3}",
            description="ThermoPro with OR",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class OrParser3(_BaseStub):
            pass

        # Both criteria match — should still return parser only once
        ad = _make_ad(
            manufacturer_data=b"\xC2\x00\x01\x02",
            local_name="TP357 (2B54)",
        )
        matches = registry.match(ad)

        assert len(matches) == 1

    def test_no_match_when_neither_criterion_matches(self):
        registry = ParserRegistry()

        @register_parser(
            name="test_or_neither",
            company_id=0x00C2,
            local_name_pattern=r"^TP\d{3}",
            description="ThermoPro with OR",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class OrParser4(_BaseStub):
            pass

        ad = _make_ad(
            manufacturer_data=b"\x4c\x00\x10\x05",
            local_name="SomethingElse",
        )
        matches = registry.match(ad)

        assert len(matches) == 0


# ===================================================================
# 5. Multiple parsers matching the same advertisement
# ===================================================================

class TestMultipleParsersMatch:
    def test_two_parsers_match_same_ad(self):
        registry = ParserRegistry()

        @register_parser(
            name="parser_a",
            company_id=0x004C,
            description="Parser A",
            version="1.0.0",
            core=True,
            registry=registry,
        )
        class ParserA(_BaseStub):
            pass

        @register_parser(
            name="parser_b",
            company_id=0x004C,
            description="Parser B",
            version="2.0.0",
            core=True,
            registry=registry,
        )
        class ParserB(_BaseStub):
            pass

        ad = _make_ad(manufacturer_data=b"\x4c\x00\x10\x05\x01")
        matches = registry.match(ad)

        assert len(matches) == 2
        types = {type(m) for m in matches}
        assert types == {ParserA, ParserB}

    def test_parsers_with_different_criteria_match_same_ad(self):
        registry = ParserRegistry()

        @register_parser(
            name="by_company",
            company_id=0x004C,
            description="By company",
            version="1.0.0",
            core=True,
            registry=registry,
        )
        class ByCompany(_BaseStub):
            pass

        @register_parser(
            name="by_name",
            local_name_pattern=r"^iPhone",
            description="By name",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class ByName(_BaseStub):
            pass

        ad = _make_ad(
            manufacturer_data=b"\x4c\x00\x10\x05\x01",
            local_name="iPhone 15",
        )
        matches = registry.match(ad)

        assert len(matches) == 2


# ===================================================================
# 6. No match returns empty list
# ===================================================================

class TestNoMatch:
    def test_empty_registry_returns_empty(self):
        registry = ParserRegistry()
        ad = _make_ad(manufacturer_data=b"\x4c\x00\x10\x05\x01")
        matches = registry.match(ad)

        assert matches == []

    def test_no_criteria_met_returns_empty(self):
        registry = ParserRegistry()

        @register_parser(
            name="specific",
            company_id=0xFFFF,
            description="Very specific",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class SpecificParser(_BaseStub):
            pass

        ad = _make_ad(manufacturer_data=b"\x06\x00\x01\x02")
        matches = registry.match(ad)

        assert matches == []

    def test_ad_with_no_identifiers_returns_empty(self):
        registry = ParserRegistry()

        @register_parser(
            name="needs_something",
            company_id=0x004C,
            description="Needs company ID",
            version="1.0.0",
            core=True,
            registry=registry,
        )
        class NeedsSomething(_BaseStub):
            pass

        ad = _make_ad()  # no manufacturer_data, no service_uuids, no local_name
        matches = registry.match(ad)

        assert matches == []


# ===================================================================
# 7. Parser metadata stored correctly
# ===================================================================

class TestParserMetadata:
    def test_metadata_name(self):
        registry = ParserRegistry()

        @register_parser(
            name="meta_test",
            company_id=0x1234,
            description="Metadata test parser",
            version="2.5.1",
            core=True,
            registry=registry,
        )
        class MetaParser(_BaseStub):
            pass

        parser_info = registry.get_by_name("meta_test")
        assert parser_info is not None
        assert parser_info.name == "meta_test"

    def test_metadata_description(self):
        registry = ParserRegistry()

        @register_parser(
            name="meta_desc",
            company_id=0x1234,
            description="A detailed description",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class MetaDescParser(_BaseStub):
            pass

        parser_info = registry.get_by_name("meta_desc")
        assert parser_info.description == "A detailed description"

    def test_metadata_version(self):
        registry = ParserRegistry()

        @register_parser(
            name="meta_ver",
            company_id=0x1234,
            description="Version check",
            version="3.2.1",
            core=False,
            registry=registry,
        )
        class MetaVerParser(_BaseStub):
            pass

        parser_info = registry.get_by_name("meta_ver")
        assert parser_info.version == "3.2.1"

    def test_metadata_core_flag_true(self):
        registry = ParserRegistry()

        @register_parser(
            name="meta_core_true",
            company_id=0x1234,
            description="Core parser",
            version="1.0.0",
            core=True,
            registry=registry,
        )
        class MetaCoreParser(_BaseStub):
            pass

        parser_info = registry.get_by_name("meta_core_true")
        assert parser_info.core is True

    def test_metadata_core_flag_false(self):
        registry = ParserRegistry()

        @register_parser(
            name="meta_core_false",
            company_id=0x1234,
            description="Plugin parser",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class MetaPluginParser(_BaseStub):
            pass

        parser_info = registry.get_by_name("meta_core_false")
        assert parser_info.core is False


# ===================================================================
# 8. get_all() returns all registered parsers
# ===================================================================

class TestGetAll:
    def test_get_all_empty_registry(self):
        registry = ParserRegistry()
        assert registry.get_all() == []

    def test_get_all_returns_all_registered(self):
        registry = ParserRegistry()

        @register_parser(
            name="all_a",
            company_id=0x0001,
            description="Parser A",
            version="1.0.0",
            core=True,
            registry=registry,
        )
        class AllA(_BaseStub):
            pass

        @register_parser(
            name="all_b",
            service_uuid="0000fff6-0000-1000-8000-00805f9b34fb",
            description="Parser B",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class AllB(_BaseStub):
            pass

        @register_parser(
            name="all_c",
            local_name_pattern=r"^Test",
            description="Parser C",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class AllC(_BaseStub):
            pass

        all_parsers = registry.get_all()
        assert len(all_parsers) == 3
        names = {p.name for p in all_parsers}
        assert names == {"all_a", "all_b", "all_c"}


# ===================================================================
# 9. get_by_name() returns specific parser or None
# ===================================================================

class TestGetByName:
    def test_returns_parser_by_name(self):
        registry = ParserRegistry()

        @register_parser(
            name="findable",
            company_id=0x9999,
            description="Findable parser",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class Findable(_BaseStub):
            pass

        result = registry.get_by_name("findable")
        assert result is not None
        assert result.name == "findable"

    def test_returns_none_for_unknown_name(self):
        registry = ParserRegistry()
        result = registry.get_by_name("nonexistent")
        assert result is None

    def test_returns_none_from_empty_registry(self):
        registry = ParserRegistry()
        result = registry.get_by_name("anything")
        assert result is None


# ===================================================================
# 10. Decorator preserves class identity
# ===================================================================

class TestDecoratorPreservesClass:
    def test_decorated_class_is_same_class(self):
        registry = ParserRegistry()

        @register_parser(
            name="identity_check",
            company_id=0xAAAA,
            description="Identity test",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class OriginalClass(_BaseStub):
            pass

        assert OriginalClass.__name__ == "OriginalClass"

    def test_decorated_class_is_instantiable(self):
        registry = ParserRegistry()

        @register_parser(
            name="instantiable",
            company_id=0xBBBB,
            description="Instantiable test",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class InstantiableClass(_BaseStub):
            pass

        instance = InstantiableClass()
        assert isinstance(instance, InstantiableClass)
        assert instance.parse(None) is None

    def test_decorated_class_retains_custom_methods(self):
        registry = ParserRegistry()

        @register_parser(
            name="custom_method",
            company_id=0xCCCC,
            description="Custom method test",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class CustomClass(_BaseStub):
            def custom_method(self):
                return 42

        instance = CustomClass()
        assert instance.custom_method() == 42


# ===================================================================
# 11. Register a parser by mac_prefix, verify it matches
# ===================================================================

class TestMatchByMacPrefix:
    def test_matches_single_mac_prefix(self):
        registry = ParserRegistry()

        @register_parser(
            name="test_mac_single",
            mac_prefix="D4:11:D6",
            description="SoundThinking OUI",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class MacParser(_BaseStub):
            pass

        ad = _make_ad(mac_address="D4:11:D6:AA:BB:CC")
        matches = registry.match(ad)

        assert len(matches) == 1
        assert isinstance(matches[0], MacParser)

    def test_matches_mac_prefix_case_insensitive(self):
        registry = ParserRegistry()

        @register_parser(
            name="test_mac_case",
            mac_prefix="d4:11:d6",
            description="Lowercase OUI",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class MacCaseParser(_BaseStub):
            pass

        ad = _make_ad(mac_address="D4:11:D6:AA:BB:CC")
        matches = registry.match(ad)

        assert len(matches) == 1

    def test_matches_mac_prefix_list(self):
        registry = ParserRegistry()

        @register_parser(
            name="test_mac_list",
            mac_prefix=["D4:11:D6", "EC:1B:BD"],
            description="Multiple OUIs",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class MacListParser(_BaseStub):
            pass

        ad1 = _make_ad(mac_address="D4:11:D6:AA:BB:CC")
        ad2 = _make_ad(mac_address="EC:1B:BD:11:22:33")
        ad3 = _make_ad(mac_address="AA:BB:CC:DD:EE:FF")

        assert len(registry.match(ad1)) == 1
        assert len(registry.match(ad2)) == 1
        assert len(registry.match(ad3)) == 0

    def test_does_not_match_different_mac(self):
        registry = ParserRegistry()

        @register_parser(
            name="test_mac_miss",
            mac_prefix="D4:11:D6",
            description="SoundThinking only",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class MacMissParser(_BaseStub):
            pass

        ad = _make_ad(mac_address="AA:BB:CC:DD:EE:FF")
        matches = registry.match(ad)

        assert len(matches) == 0

    def test_mac_prefix_or_with_other_criteria(self):
        """mac_prefix participates in OR logic with other criteria."""
        registry = ParserRegistry()

        @register_parser(
            name="test_mac_or",
            mac_prefix="D4:11:D6",
            company_id=0x09C8,
            description="MAC or company ID",
            version="1.0.0",
            core=False,
            registry=registry,
        )
        class MacOrParser(_BaseStub):
            pass

        # Match by MAC only
        ad_mac = _make_ad(mac_address="D4:11:D6:AA:BB:CC")
        assert len(registry.match(ad_mac)) == 1

        # Match by company_id only
        ad_cid = _make_ad(
            mac_address="AA:BB:CC:DD:EE:FF",
            manufacturer_data=b"\xC8\x09\x01\x02",
        )
        assert len(registry.match(ad_cid)) == 1


# ===================================================================
# Additional edge cases
# ===================================================================

