"""Tests for vendor lookup module."""

import pytest

from adwatch.vendors import bt_company_name, oui_vendor, best_vendor


class TestBtCompanyName:
    def test_known_company(self):
        assert bt_company_name(0x004C) == "Apple, Inc."

    def test_known_company_microsoft(self):
        assert bt_company_name(0x0006) == "Microsoft"

    def test_known_company_google(self):
        assert bt_company_name(0x00E0) == "Google"

    def test_unknown_company(self):
        assert bt_company_name(0xDEAD) is None

    def test_none_input(self):
        assert bt_company_name(None) is None

    def test_zero(self):
        # 0x0000 is Ericsson AB
        result = bt_company_name(0x0000)
        assert result is not None


class TestOuiVendor:
    def test_known_oui_apple(self):
        result = oui_vendor("00:03:93:00:11:22")
        assert result == "Apple, Inc."

    def test_known_oui_intel(self):
        result = oui_vendor("00:02:B3:AA:BB:CC")
        assert result == "Intel Corporation"

    def test_unknown_oui(self):
        assert oui_vendor("FF:FF:FF:00:00:00") is None

    def test_random_mac_ignored(self):
        """Random MAC addresses have bit 1 of first octet set."""
        # This is a random/local MAC (second hex digit is odd in bit 1)
        # but oui_vendor just does prefix lookup regardless
        result = oui_vendor("FA:FB:FC:00:00:00")
        # May or may not match, just shouldn't crash
        assert result is None or isinstance(result, str)

    def test_none_input(self):
        assert oui_vendor(None) is None

    def test_empty_string(self):
        assert oui_vendor("") is None

    def test_case_insensitive(self):
        r1 = oui_vendor("00:03:93:aa:bb:cc")
        r2 = oui_vendor("00:03:93:AA:BB:CC")
        assert r1 == r2


class TestBestVendor:
    def test_prefers_bt_company_over_oui(self):
        """BT SIG company ID is more specific than OUI."""
        result = best_vendor(
            mac="00:03:93:00:11:22",
            address_type="public",
            company_id=0x004C,
        )
        assert result == "Apple, Inc."

    def test_falls_back_to_oui_for_public_mac(self):
        result = best_vendor(
            mac="00:03:93:00:11:22",
            address_type="public",
            company_id=None,
        )
        assert result is not None
        assert "Apple" in result

    def test_no_oui_for_random_mac(self):
        """OUI is meaningless for random MACs."""
        result = best_vendor(
            mac="FA:FB:FC:00:00:00",
            address_type="random",
            company_id=None,
        )
        assert result is None

    def test_bt_company_even_with_random_mac(self):
        """BT SIG company ID works regardless of MAC type."""
        result = best_vendor(
            mac="FA:FB:FC:00:00:00",
            address_type="random",
            company_id=0x004C,
        )
        assert result == "Apple, Inc."

    def test_none_everything(self):
        assert best_vendor(mac=None, address_type=None, company_id=None) is None
