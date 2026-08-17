"""The Maytronics bare-serial catch-all must not swallow Ecowitt consoles.

`maytronics.py` accepts any 8-character alphanumeric name containing a digit as
a Dolphin serial number.  `WS1900AB` and `HP1012CD` are Ecowitt / Ambient
Weather console names of exactly that shape, so both plugins claimed them.
The Ecowitt prefixes are far more specific, so the catch-all yields.
"""

import pytest

from adwatch.models import RawAdvertisement
from adwatch.plugins.ecowitt import EcowittParser
from adwatch.plugins.maytronics import MaytronicsParser


def _ad(name):
    return RawAdvertisement(
        timestamp="2026-08-16T00:00:00Z",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="public",
        manufacturer_data=None,
        service_data=None,
        local_name=name,
    )


@pytest.mark.parametrize("name", ["WS1900AB", "WS1950XY", "HP1012CD"])
def test_maytronics_does_not_claim_ecowitt_names(name):
    assert MaytronicsParser().parse(_ad(name)) is None


@pytest.mark.parametrize("name", ["WS1900AB", "WS1950XY", "HP1012CD"])
def test_ecowitt_still_claims_them(name):
    result = EcowittParser().parse(_ad(name))
    assert result is not None
    assert result.parser_name == "ecowitt"


@pytest.mark.parametrize("name", ["A1B2C3D4", "Dolphin1", "12ab34CD56ef", "IoT_PWS"])
def test_maytronics_bare_serials_still_match(name):
    assert MaytronicsParser().parse(_ad(name)) is not None


def test_ambweather_never_reaches_the_catch_all():
    """`AMBWeather-4F2A` has a dash and is 15 chars, so the 8-alphanumeric
    bare-serial branch cannot fire for it in the first place."""
    assert MaytronicsParser().parse(_ad("AMBWeather-4F2A")) is None
    assert EcowittParser().parse(_ad("AMBWeather-4F2A")) is not None
