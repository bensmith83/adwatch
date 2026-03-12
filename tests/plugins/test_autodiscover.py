"""Tests for plugin auto-discovery."""

import importlib

import adwatch.plugins  # noqa: F401 — triggers auto-discovery

from adwatch.registry import _default_registry


class TestAutoDiscover:
    def test_govee_registered_without_explicit_import(self):
        """Govee should be auto-discovered from the plugins directory."""
        names = [p.name for p in _default_registry.get_all()]
        assert "govee" in names

    def test_all_register_parser_plugins_discovered(self):
        """Every plugin using @register_parser should be auto-discovered."""
        expected = {
            "thermopro", "matter", "tile", "smarttag", "smart_glasses",
            "switchbot", "google_fmd", "oralb", "tilt",
            "exposure_notification", "inkbird", "bt_mesh", "qingping",
            "govee", "ruuvi", "bthome", "mibeacon", "eddystone",
        }
        names = {p.name for p in _default_registry.get_all()}
        assert expected.issubset(names), f"Missing: {expected - names}"

    def test_init_has_no_hardcoded_imports(self):
        """plugins/__init__.py should not have a hardcoded import list."""
        source = importlib.util.find_spec("adwatch.plugins").origin
        with open(source) as f:
            content = f.read()
        assert "from adwatch.plugins import (" not in content
