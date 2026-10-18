import json

import pytest

from porchlight.resolver import (
    FieldTable,
    Resolver,
    SharedGuard,
    bits_of,
    classify_address,
    is_bad_mac,
    is_junk,
    stable_remainder,
)

from parser_paths import FIELDS

RULES = {
    "weak_bits": 24,
    "shared_if_concurrent_addresses": 3,
    "name_token_regex": "[0-9A-Fa-f]{4,}|\\d{3,}",
    "skip_stable_key_prefixes": ["eddystone_eid:"],
}


def row(parser, key, source="meta", confidence="high", mobility="personal", **kw):
    return {"source": source, "parser": parser, "key": key, "id_type": kw.get("id_type", "Serial"),
            "confidence": confidence, "vendor": kw.get("vendor", parser.title()),
            "product": kw.get("product", parser + " thing"), "category": "x", "mobility": mobility}


def family(parser, prefix, confidence="medium", mobility="fixed"):
    return {"parser": parser, "prefix": prefix, "id_type": "Name suffix", "confidence": confidence,
            "vendor": parser.title(), "product": parser + " named", "mobility": mobility, "min_token_bits": 16}


TABLE = {
    "fields": [
        row("whoop", "serial"),
        row("whoop", "stableKey", source="stableKey"),
        row("sonos", "device_id", mobility="fixed", vendor="Sonos"),
        row("sonos", "stableKey", source="stableKey", mobility="fixed"),
        row("shokz", "embedded_address"),
        row("oura_ring", "stableKey", source="stableKey", confidence="low"),
        row("acme_appliance", "device_id", mobility="fixed"),
        row("eddy", "stableKey", source="stableKey"),
    ],
    "name_families": [
        family("sonos", "S39 "),
        family("smartthings", "S", confidence="high", mobility="vehicle"),
        family("unparsed", "LED_BLE_"),
    ],
    "unreliable_parsers": ["acme_appliance"],
    "rules": RULES,
}


def ad(addr="C0:FF:EE:00:00:01", atype="random", name=None, rssi=-60, t=1_760_000_000_000):
    return {"t": t, "addr": addr, "atype": atype, "rssi": rssi, "mfr": None, "svc": {}, "uuids": [], "name": name, "tx": None}


def result(parser, metadata=None, stableKey=None):
    return {"parser": parser, "beaconType": parser, "deviceClass": "x", "stableKey": stableKey, "metadata": metadata or {}}


@pytest.fixture
def resolver():
    return Resolver(FieldTable.from_dict(TABLE))


def keys(res):
    return sorted(k.key for k in res)


# --- payload IDs -------------------------------------------------------------

def test_listed_meta_field_gives_an_id_key(resolver):
    out = resolver.resolve(ad(addr="40:00:00:00:00:01"), [result("whoop", {"serial": "TEST0001", "model_family": "WHOOP 4"})])
    assert keys(out) == ["id:whoop:serial:TEST0001"]
    k = out[0]
    assert k.kind == "id" and k.parser == "whoop" and k.mobility == "personal"
    assert k.vendor == "Whoop" and k.id_type == "Serial" and k.confidence == "high"


def test_listed_stable_key_gives_an_sk_key(resolver):
    out = resolver.resolve(ad(addr="40:00:00:00:00:01"), [result("whoop", {}, stableKey="TEST0001")])
    assert keys(out) == ["sk:whoop:TEST0001"]


def test_unlisted_parser_or_key_gives_nothing(resolver):
    out = resolver.resolve(ad(addr="40:00:00:00:00:01"), [result("whoop", {"battery": "88"}), result("acme", {"serial": "TEST0002"}, stableKey="X1234")])
    assert out == []


def test_same_radio_values_from_several_results_all_come_out(resolver):
    out = resolver.resolve(
        ad(addr="40:00:00:00:00:01", name="S39 ABCD LE"),
        [result("sonos", {"device_id": "c0ffee000001"}, stableKey="sonos:c0ffee000001")],
    )
    assert keys(out) == ["id:sonos:device_id:c0ffee000001", "name:sonos:S39 ABCD LE", "sk:sonos:sonos:c0ffee000001"]


# --- names -------------------------------------------------------------------

def test_name_family_needs_a_token_after_the_prefix(resolver):
    assert keys(resolver.resolve(ad(addr="40:00:00:00:00:01", name="S39 ABCD LE"), [result("sonos")])) == ["name:sonos:S39 ABCD LE"]
    assert resolver.resolve(ad(addr="40:00:00:00:00:01", name="S39 Kitchen"), [result("sonos")]) == []


def test_name_is_attributed_to_each_result_parser(resolver):
    out = resolver.resolve(ad(addr="40:00:00:00:00:01", name="S0123456789abcdefC"), [result("tesla"), result("smartthings")])
    assert keys(out) == ["name:smartthings:S0123456789abcdefC"]


def test_unparsed_families_apply_only_when_nothing_parsed(resolver):
    assert keys(resolver.resolve(ad(addr="40:00:00:00:00:01", name="LED_BLE_C0FFEE01"), [])) == ["name:unparsed:LED_BLE_C0FFEE01"]
    assert resolver.resolve(ad(addr="40:00:00:00:00:01", name="LED_BLE_C0FFEE01"), [result("acme")]) == []


def test_a_name_with_no_family_is_not_an_identity(resolver):
    assert resolver.resolve(ad(addr="40:00:00:00:00:01", name="Thing_C0FFEE01"), []) == []


def test_name_bits_come_from_the_tokens(resolver):
    (k,) = resolver.resolve(ad(addr="40:00:00:00:00:01", name="S39 ABCD LE"), [result("sonos")])
    assert k.bits == 16 and k.weak
    (k,) = resolver.resolve(ad(addr="40:00:00:00:00:01", name="S0123456789abcdefC"), [result("smartthings")])
    assert k.bits == 68 and not k.weak  # the trailing "C" is hex too


# --- junk, bad MACs, unreliable parsers, confidence ---------------------------

@pytest.mark.parametrize("value", ["000000", "00:00:00", "FFFFFFFF", "ff-ff-ff", "----", "aaaa", "7", ""])
def test_junk_values_are_dropped(resolver, value):
    assert is_junk(value)
    assert resolver.resolve(ad(addr="40:00:00:00:00:01"), [result("whoop", {"serial": value})]) == []


@pytest.mark.parametrize("value", ["TEST0001", "c0ffee000001", "ab"])
def test_real_looking_values_are_not_junk(value):
    assert not is_junk(value)


def test_stable_keys_are_junk_checked_after_their_word_prefix(resolver):
    assert stable_remainder("sonos:000000000000") == "000000000000"
    assert stable_remainder("whoop_mode:AT") == "AT"
    assert resolver.resolve(ad(addr="40:00:00:00:00:01"), [result("sonos", {}, stableKey="sonos:000000000000")]) == []
    assert resolver.resolve(ad(addr="40:00:00:00:00:01"), [result("sonos", {}, stableKey="sonos:ffffffffffff")]) == []


def test_stable_remainder_does_not_eat_mac_octets_that_happen_to_be_letters():
    assert stable_remainder("mac:AA:BB:CC:DD:EE:01") == "AA:BB:CC:DD:EE:01"


def test_eddystone_eid_stable_keys_are_skipped(resolver):
    assert resolver.resolve(ad(addr="40:00:00:00:00:01"), [result("eddy", {}, stableKey="eddystone_eid:0123456789abcdef")]) == []


@pytest.mark.parametrize("value, bad", [
    ("00:00:00:00:12:34", True),    # 4 zero octets
    ("01:23:45:67:89:AB", True),    # multicast bit set in both byte orders
    ("01:23:45:67:89:AA", False),   # multicast only in one byte order
    ("C0:FF:EE:00:00:02", False),
    ("C0FFEE000002", False),
    ("0000", False),                # not a 12-hex value: not judged as a MAC
])
def test_bad_embedded_macs(value, bad):
    assert is_bad_mac(value) is bad


def test_bad_embedded_macs_are_dropped_only_for_mac_like_keys(resolver):
    assert resolver.resolve(ad(addr="40:00:00:00:00:01"), [result("shokz", {"embedded_address": "00:00:00:00:12:34"})]) == []
    out = resolver.resolve(ad(addr="40:00:00:00:00:01"), [result("shokz", {"embedded_address": "C0:FF:EE:00:00:09"})])
    assert keys(out) == ["id:shokz:embedded_address:C0:FF:EE:00:00:09"]


def test_unreliable_parsers_are_skipped_even_when_listed(resolver):
    assert resolver.resolve(ad(addr="40:00:00:00:00:01"), [result("acme_appliance", {"device_id": "TEST0003"})]) == []


def test_low_confidence_rows_are_opt_in():
    table = FieldTable.from_dict(TABLE)
    r = [result("oura_ring", {}, stableKey="TEST0004")]
    assert Resolver(table).resolve(ad(addr="40:00:00:00:00:01"), r) == []
    assert keys(Resolver(table, include_low_confidence=True).resolve(ad(addr="40:00:00:00:00:01"), r)) == ["sk:oura_ring:TEST0004"]


# --- stable MAC ----------------------------------------------------------------

@pytest.mark.parametrize("addr, atype, kind", [
    ("00:11:22:33:44:55", "public", "public"),
    ("C0:FF:EE:00:00:01", "random", "random_static"),
    ("40:FF:EE:00:00:01", "random", "resolvable_private"),
    ("00:FF:EE:00:00:01", "random", "non_resolvable_private"),
    ("80:FF:EE:00:00:01", "random", "reserved"),
])
def test_address_classification(addr, atype, kind):
    assert classify_address(atype, addr) == kind


@pytest.mark.parametrize("addr, atype, stable", [
    ("00:11:22:33:44:55", "public", True),
    ("c0:ff:ee:00:00:01", "random", True),
    ("40:FF:EE:00:00:01", "random", False),
    ("00:FF:EE:00:00:01", "random", False),
    ("80:FF:EE:00:00:01", "random", False),
])
def test_stable_mac_key(resolver, addr, atype, stable):
    out = resolver.resolve(ad(addr=addr, atype=atype), [])
    if stable:
        (k,) = out
        assert k.key == "mac:" + addr.upper()
        assert k.kind == "mac" and k.bits == 48 and not k.weak
        assert k.hint == addr.replace(":", "")[-4:].upper()
    else:
        assert out == []


# --- strength and hints ----------------------------------------------------------

@pytest.mark.parametrize("text, bits", [
    ("123", 9.96),          # digits
    ("ABCD", 16),           # hex
    ("WXYZ", 20.68),        # other alnum
    ("AB:12", 8 + 6.64),    # per token, summed
    ("", 0),
])
def test_bits(text, bits):
    assert bits_of(text) == pytest.approx(bits, abs=0.05)


def test_weak_is_under_24_bits(resolver):
    (k,) = resolver.resolve(ad(addr="40:00:00:00:00:01"), [result("whoop", {"serial": "ABCDE"})])
    assert k.bits == 20 and k.weak
    (k,) = resolver.resolve(ad(addr="40:00:00:00:00:01"), [result("whoop", {"serial": "ABCDEF"})])
    assert k.bits == 24 and not k.weak


def test_hint_is_the_last_four_characters(resolver):
    (k,) = resolver.resolve(ad(addr="40:00:00:00:00:01"), [result("sonos", {"device_id": "c0ffee003f2a"})])
    assert k.hint == "3F2A"
    (k,) = resolver.resolve(ad(addr="40:00:00:00:00:01", name="S39 ABCD LE"), [result("sonos")])
    assert k.hint == "ABCD"


# --- shared-value guard --------------------------------------------------------

def test_three_addresses_within_60s_mark_a_key_shared():
    g = SharedGuard()
    assert not g.observe("k", "A", 0.0)
    assert not g.observe("k", "B", 30.0)
    assert g.observe("k", "C", 59.0)
    assert g.is_shared("k")
    assert g.observe("k", "A", 10_000.0), "shared stays shared"


def test_addresses_spread_beyond_60s_are_not_shared():
    g = SharedGuard()
    g.observe("k", "A", 0.0)
    g.observe("k", "B", 30.0)
    assert not g.observe("k", "C", 61.0)


def test_one_address_repeating_is_not_shared():
    g = SharedGuard()
    for t in range(100):
        assert not g.observe("k", "A", float(t))


def test_guard_can_start_from_persisted_shared_keys():
    g = SharedGuard(shared={"k"})
    assert g.is_shared("k")


def test_guard_forgets_quiet_keys():
    g = SharedGuard()
    g.observe("k", "A", 0.0)
    g.prune(1000.0)
    assert g.tracked() == 0


# --- a table file -----------------------------------------------------------------

def test_a_table_file_loads():
    table = FieldTable.load(FIELDS)
    r = Resolver(table)
    out = r.resolve(ad(addr="40:00:00:00:00:01", name="S39 ABCD LE"),
                    [result("sonos", {"device_id": "c0ffee000001", "device_suffix": "ABCD"}, stableKey="sonos:c0ffee000001")])
    kinds = {k.kind for k in out}
    assert {"id", "sk", "name"} <= kinds
    assert all(k.mobility == "fixed" for k in out)
    assert table.weak_bits == 24
    assert table.unreliable, "the unreliable parsers load"
