"""
Parser acceptance on real-world XMLTV data (D-15).

The committed excerpt `tests/fixtures/real_de_excerpt.xml` is deferred by the user's decision in 01-09 (Task 2:
"none"), so this module skips while it is absent. Set `XMLTV_REAL_FEED` to a local plain or gzip feed to run the
same checks against it without committing anything.
"""

import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from custom_components.xmltv_calendar.xmltv.filter import FilterSpec
from custom_components.xmltv_calendar.xmltv.parser import parse

if TYPE_CHECKING:
    from custom_components.xmltv_calendar.xmltv.model import EpgData

EXCERPT = Path(__file__).parent.parent / "fixtures" / "real_de_excerpt.xml"
FEED = Path(os.environ.get("XMLTV_REAL_FEED") or EXCERPT)

if not FEED.is_file():
    pytest.skip(
        f"no real XMLTV feed: {EXCERPT.name} is deferred (D-15, 01-09); set XMLTV_REAL_FEED to run these checks",
        allow_module_level=True,
    )


@pytest.fixture(scope="module")
def epg() -> EpgData:
    with FEED.open("rb") as fileobj:
        return parse(fileobj, keep_after=None)


def test_feed_has_programmes(epg: EpgData) -> None:
    assert epg.programmes
    assert epg.stats.programmes == len(epg.programmes)


def test_malformed_share_is_at_most_one_percent(epg: EpgData) -> None:
    assert epg.stats.skipped_malformed <= epg.stats.programmes * 0.01


def test_times_are_aware_and_ordered(epg: EpgData) -> None:
    for programme in epg.programmes:
        assert programme.start.utcoffset() is not None, programme
        assert programme.stop.utcoffset() is not None, programme
        assert programme.stop >= programme.start, programme


def test_channels_are_known_and_named(epg: EpgData) -> None:
    assert all(programme.channel_id in epg.channels for programme in epg.programmes)
    assert all(channel.display_name.strip() for channel in epg.channels.values())


def test_anchored_title_pattern_matches_first_programme(epg: EpgData) -> None:
    first = epg.programmes[0]
    spec = FilterSpec.from_mapping({"channels": [first.channel_id], "include": f"^{re.escape(first.titles[0])}$"})

    assert first in spec.apply(epg).matches
