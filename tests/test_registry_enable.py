"""Tests for ParserRegistry enable/disable feature."""

import pytest

from adwatch.models import RawAdvertisement
from adwatch.registry import ParserRegistry, register_parser


@pytest.fixture
def registry():
    return ParserRegistry()


@pytest.fixture
def registry_with_parser(registry):
    """Registry with a single registered parser."""

    @register_parser(
        name="test_parser",
        local_name_pattern=r"^TEST",
        description="Test parser",
        version="1.0.0",
        core=False,
        registry=registry,
    )
    class TestParser:
        def parse(self, raw):
            return None

    return registry


@pytest.fixture
def raw_ad():
    return RawAdvertisement(
        timestamp="2025-01-15T10:00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        manufacturer_data=None,
        service_data=None,
        local_name="TEST-device",
    )


class TestRegistryEnableDisable:
    def test_disable_parser_skips_match(self, registry_with_parser, raw_ad):
        """set_enabled(name, False) should cause match() to skip that parser."""
        # Verify it matches first
        assert len(registry_with_parser.match(raw_ad)) == 1

        registry_with_parser.set_enabled("test_parser", False)
        assert len(registry_with_parser.match(raw_ad)) == 0

    def test_reenable_parser_restores_match(self, registry_with_parser, raw_ad):
        """set_enabled(name, True) should re-enable the parser."""
        registry_with_parser.set_enabled("test_parser", False)
        assert len(registry_with_parser.match(raw_ad)) == 0

        registry_with_parser.set_enabled("test_parser", True)
        assert len(registry_with_parser.match(raw_ad)) == 1

    def test_get_all_includes_enabled_field(self, registry_with_parser):
        """get_all() should include an enabled field on each ParserInfo."""
        parsers = registry_with_parser.get_all()
        assert len(parsers) == 1
        assert hasattr(parsers[0], "enabled")
        assert parsers[0].enabled is True

    def test_get_all_reflects_disabled_state(self, registry_with_parser):
        """get_all() should show enabled=False after disabling."""
        registry_with_parser.set_enabled("test_parser", False)
        parsers = registry_with_parser.get_all()
        assert parsers[0].enabled is False

    def test_set_enabled_nonexistent_raises(self, registry_with_parser):
        """set_enabled on a non-existent parser should raise ValueError."""
        with pytest.raises(ValueError):
            registry_with_parser.set_enabled("nonexistent_parser", False)
