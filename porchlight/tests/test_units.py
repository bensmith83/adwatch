import pytest

from porchlight.model import NO_MOBILITY_RANK
from porchlight.resolver import FieldTable, IdentityKey
from porchlight.store import Store
from porchlight.units import RADIO_WINDOW_S, UnitBook

TABLE = FieldTable.from_dict({
    "fields": [
        {"source": "meta", "parser": "sonos", "key": "device_id", "id_type": "Vendor device ID",
         "confidence": "high", "vendor": "Sonos", "product": "Speaker", "mobility": "fixed"},
        {"source": "meta", "parser": "acme", "key": "serial", "id_type": "Serial",
         "confidence": "medium", "vendor": "Acme", "product": "Tag", "mobility": "personal"},
        {"source": "meta", "parser": "acme", "key": "other", "id_type": "Serial",
         "confidence": "medium", "vendor": "Acme", "product": "Tag", "mobility": "personal"},
        {"source": "meta", "parser": "acme", "key": "third", "id_type": "Serial",
         "confidence": "medium", "vendor": "Acme", "product": "Tag", "mobility": "vehicle"},
    ],
    "name_families": [], "unreliable_parsers": [], "rules": {},
})


def key(name, bits=48.0, kind="id", mobility="personal", confidence="high", vendor="Acme", product="Tag",
        id_type="Serial"):
    return IdentityKey(key=f"{kind}:{name}", kind=kind, parser="acme", bits=bits, weak=bits < 24,
                       hint=name[-4:].upper(), id_type=id_type, confidence=confidence, vendor=vendor,
                       product=product, mobility=mobility)


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "p.db")
    yield s
    s.close()


@pytest.fixture
def book(store):
    return UnitBook(TABLE, store)


def see(book, store, keys, addr="40:00:00:00:00:01", t=0.0, parsers=("acme",)):
    return book.observe([(k, store.hmac(k.key)) for k in keys], addr, t, list(parsers))


def test_first_sighting_makes_a_unit_and_files_its_keys(book, store):
    obs = see(book, store, [key("a001"), key("b001", kind="sk")])
    assert obs.new_unit
    u = obs.unit
    assert u.first_seen == u.last_seen == 0.0
    assert {book.keys[store.hmac("id:a001")].unit_id, book.keys[store.hmac("sk:b001")].unit_id} == {u.id}
    assert not u.weak


def test_keys_from_one_ad_stay_together_and_new_keys_join(book, store):
    u1 = see(book, store, [key("a001")], addr="40:00:00:00:00:01", t=0).unit
    obs = see(book, store, [key("a001"), key("c001")], addr="40:00:00:00:00:02", t=100)
    assert obs.unit.id == u1.id and not obs.new_unit
    assert book.keys[store.hmac("id:c001")].unit_id == u1.id
    assert obs.unit.last_seen == 100


def test_same_address_within_10_minutes_is_the_same_radio(book, store):
    u1 = see(book, store, [key("a001")], addr="40:00:00:00:00:01", t=0).unit
    u2 = see(book, store, [key("z001")], addr="40:00:00:00:00:01", t=RADIO_WINDOW_S).unit
    assert u2.id == u1.id


def test_same_address_after_10_minutes_is_not_evidence(book, store):
    u1 = see(book, store, [key("a001")], addr="40:00:00:00:00:01", t=0).unit
    u2 = see(book, store, [key("z001")], addr="40:00:00:00:00:01", t=RADIO_WINDOW_S + 1).unit
    assert u2.id != u1.id


def test_a_strong_key_merges_two_units_into_the_older(book, store):
    u1 = see(book, store, [key("a001")], addr="40:00:00:00:00:01", t=0).unit
    u2 = see(book, store, [key("b001")], addr="40:00:00:00:00:02", t=10).unit
    obs = see(book, store, [key("a001"), key("b001")], addr="40:00:00:00:00:03", t=2000)
    assert obs.unit.id == u1.id
    assert obs.merged == [u2.id]
    assert u2.id not in book.units
    assert book.keys[store.hmac("id:b001")].unit_id == u1.id
    store.flush()
    assert set(store.load().units) == {u1.id}


def test_weak_keys_never_merge_two_units(book, store):
    ux = see(book, store, [key("w001", bits=16)], addr="40:00:00:00:00:01", t=0).unit
    uy = see(book, store, [key("s001")], addr="40:00:00:00:00:02", t=10).unit
    obs = see(book, store, [key("s001"), key("w001", bits=16)], addr="40:00:00:00:00:03", t=2000)
    assert obs.unit.id == uy.id
    assert obs.merged == []
    assert ux.id in book.units
    assert book.keys[store.hmac("id:w001")].unit_id == ux.id, "the weak key stays where it was"


def test_a_weak_key_alone_finds_its_unit_again(book, store):
    u = see(book, store, [key("w001", bits=16)], addr="40:00:00:00:00:01", t=0).unit
    assert u.weak
    obs = see(book, store, [key("w001", bits=16), key("w002", bits=16)], addr="40:00:00:00:00:09", t=5000)
    assert obs.unit.id == u.id
    assert book.keys[store.hmac("id:w002")].unit_id == u.id, "weak keys can join a unit"


def test_a_weak_unit_turns_strong_when_a_strong_key_joins(book, store):
    u = see(book, store, [key("w001", bits=16)], t=0).unit
    see(book, store, [key("w001", bits=16), key("s001")], t=10)
    assert not u.weak


def test_weak_keys_pointing_at_two_units_pick_one_without_merging(book, store):
    ux = see(book, store, [key("w001", bits=16)], addr="40:00:00:00:00:01", t=0).unit
    uy = see(book, store, [key("w002", bits=16)], addr="40:00:00:00:00:02", t=10).unit
    obs = see(book, store, [key("w001", bits=16), key("w002", bits=16)], addr="40:00:00:00:00:03", t=2000)
    assert obs.unit.id in (ux.id, uy.id)
    assert obs.merged == []
    assert {ux.id, uy.id} <= set(book.units)


def test_shared_keys_are_ignored(book, store):
    book.mark_shared(store.hmac("id:fleet"), "id", 48.0)
    assert see(book, store, [key("fleet")], t=0) is None
    store.flush()
    assert store.load().keys[store.hmac("id:fleet")].shared


def test_a_shared_key_already_filed_stays_shared_and_is_ignored(book, store):
    u = see(book, store, [key("fleet")], addr="40:00:00:00:00:01", t=0).unit
    book.mark_shared(store.hmac("id:fleet"), "id", 48.0)
    obs = see(book, store, [key("fleet")], addr="40:00:00:00:00:05", t=5000)
    assert obs is None
    assert u.id in book.units


def test_mobility_comes_from_the_best_confidence_known_row(book, store):
    u = see(book, store, [key("a001", mobility="unknown", confidence="high"),
                          key("b001", mobility="vehicle", confidence="medium")], t=0).unit
    assert u.mobility == "vehicle"
    see(book, store, [key("a001", mobility="unknown"), key("c001", mobility="personal", confidence="high")], t=1)
    assert u.mobility == "personal"
    see(book, store, [key("a001", mobility="unknown"), key("d001", mobility="fixed", confidence="medium")], t=2)
    assert u.mobility == "personal", "a worse row does not override"


def test_mac_only_units_take_the_parsers_majority_mobility(book, store):
    mac = IdentityKey(key="mac:C0:FF:EE:00:00:01", kind="mac", parser="", bits=48.0, weak=False, hint="0001",
                      id_type="Stable MAC address", confidence="high", vendor=None, product=None, mobility="unknown")
    u = see(book, store, [mac], addr="C0:FF:EE:00:00:01", parsers=["acme"]).unit
    assert u.mobility == "personal"  # acme rows: 2 personal, 1 vehicle
    assert u.vendor == "Acme"
    u2 = see(book, store, [IdentityKey(**{**mac.__dict__, "key": "mac:C0:FF:EE:00:00:02"})],
             addr="C0:FF:EE:00:00:02", parsers=[]).unit
    assert u2.mobility == "unknown" and u2.mobility_rank == NO_MOBILITY_RANK


def test_unit_fields_follow_the_keys(book, store):
    u = see(book, store, [key("w001", bits=16, id_type="Name suffix"), key("abcdef123456", id_type="Serial")], t=0).unit
    assert u.id_types == {"Name suffix", "Serial"}
    assert u.vendor == "Acme" and u.product == "Tag"
    assert u.hint == "3456", "the hint comes from the strongest key"


def test_book_restores_from_a_snapshot(book, store):
    u = see(book, store, [key("a001")], t=0).unit
    store.flush()
    book2 = UnitBook(TABLE, store, store.load())
    obs = see(book2, store, [key("a001")], addr="40:00:00:00:00:77", t=99999)
    assert obs.unit.id == u.id and not obs.new_unit


def test_remove_forgets_units_and_their_keys(book, store):
    u = see(book, store, [key("a001")], t=0).unit
    book.remove({u.id})
    assert u.id not in book.units
    assert store.hmac("id:a001") not in book.keys
    assert see(book, store, [key("a001")], addr="40:00:00:00:00:99", t=99999).new_unit
