"""End-to-end filter tests: subentry filter data drives what a calendar shows."""

import logging
import unicodedata
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from homeassistant.const import WEEKDAYS as HA_WEEKDAYS

from custom_components.xmltv_calendar.xmltv import settings
from custom_components.xmltv_calendar.xmltv.settings import (
    FIELD_CATEGORY,
    FIELD_TITLE,
    KEY_INCLUDE,
    KEY_INCLUDE_FIELDS,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant

BASIC_FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()


async def _summaries(hass: HomeAssistant, entity_id: str) -> list[str]:
    response = await hass.services.async_call(
        "calendar",
        "get_events",
        {"entity_id": entity_id, "start_date_time": "2026-10-13T00:00:00+00:00", "duration": {"hours": 24}},
        blocking=True,
        return_response=True,
    )
    return [event["summary"] for event in response[entity_id]["events"]]


async def test_include_pattern_end_to_end(
    hass: HomeAssistant,
    freezer: Any,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    freezer.move_to("2026-10-13T08:00:00+00:00")
    await setup_xmltv(BASIC_FEED, calendars=(("News", {"include": "^Tagesschau$"}),))

    assert await _summaries(hass, "calendar.news") == ["Das Erste: Tagesschau"]


async def test_missing_channel_warning_once_per_refresh(
    hass: HomeAssistant,
    freezer: Any,
    caplog: pytest.LogCaptureFixture,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    freezer.move_to("2026-10-13T08:00:00+00:00")
    entry = await setup_xmltv(BASIC_FEED, calendars=(("Mixed", {"channels": ["gone.de", "zdf.de"]}),))

    def missing_warnings() -> list[logging.LogRecord]:
        return [r for r in caplog.records if r.levelno == logging.WARNING and "gone.de" in r.getMessage()]

    assert len(missing_warnings()) == 1

    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()
    assert len(missing_warnings()) == 2

    assert await _summaries(hass, "calendar.mixed") == ["ZDF: heute", "ZDF: heute"]


def _feed(title: str) -> bytes:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<tv><channel id="daserste.de"><display-name>Das Erste</display-name></channel>'
        '<programme channel="daserste.de" start="20261013200000 +0200" stop="20261013213000 +0200">'
        f"<title>{title}</title></programme>"
        '<programme channel="daserste.de" start="20261013220000 +0200" stop="20261013223000 +0200">'
        "<title>Tagesthemen</title></programme></tv>"
    ).encode()


@pytest.mark.parametrize(
    ("title", "include"),
    [
        pytest.param(unicodedata.normalize("NFD", "Tatort Köln"), "köln", id="nfd-feed"),
        pytest.param("Tatort Köln", unicodedata.normalize("NFD", "köln"), id="nfd-pattern"),
    ],
)
async def test_umlaut_pattern_matches_decomposed_feed(
    hass: HomeAssistant,
    freezer: Any,
    setup_xmltv: Callable[..., Awaitable[Any]],
    title: str,
    include: str,
) -> None:
    freezer.move_to("2026-10-13T06:00:00+00:00")
    await setup_xmltv(_feed(title), calendars=(("Koeln", {"include": include}),))

    summaries = await _summaries(hass, "calendar.koeln")

    assert len(summaries) == 1
    (summary,) = summaries
    assert summary == "Das Erste: Tatort Köln"
    assert unicodedata.is_normalized("NFC", summary)


SPORT_FEED = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<tv><channel id="daserste.de"><display-name>Das Erste</display-name></channel>'
    b'<programme channel="daserste.de" start="20261013180000 +0200" stop="20261013183000 +0200">'
    b"<title>Sportschau</title><category>Sport</category></programme>"
    b'<programme channel="daserste.de" start="20261013200000 +0200" stop="20261013201500 +0200">'
    b"<title>Tagesschau</title><category>News</category><category>Sport</category>"
    b"<desc>Mit Wiederholung</desc></programme>"
    b'<programme channel="daserste.de" start="20261013220000 +0200" stop="20261013223000 +0200">'
    b"<title>Sport extra</title><category>Sportnachrichten</category></programme></tv>"
)


async def test_category_field_selection_end_to_end(
    hass: HomeAssistant,
    freezer: Any,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    freezer.move_to("2026-10-13T06:00:00+00:00")
    await setup_xmltv(
        SPORT_FEED, calendars=(("Sport", {KEY_INCLUDE: "^Sport$", KEY_INCLUDE_FIELDS: [FIELD_CATEGORY]}),)
    )

    assert await _summaries(hass, "calendar.sport") == ["Das Erste: Sportschau", "Das Erste: Tagesschau"]


async def test_two_calendars_different_fields_same_refresh(
    hass: HomeAssistant,
    freezer: Any,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    freezer.move_to("2026-10-13T06:00:00+00:00")
    entry = await setup_xmltv(
        SPORT_FEED,
        calendars=(
            ("T", {KEY_INCLUDE: "sport", KEY_INCLUDE_FIELDS: [FIELD_TITLE]}),
            ("C", {KEY_INCLUDE: "sport", KEY_INCLUDE_FIELDS: [FIELD_CATEGORY]}),
        ),
    )
    by_title = ["Das Erste: Sportschau", "Das Erste: Sport extra"]
    by_category = ["Das Erste: Sportschau", "Das Erste: Tagesschau", "Das Erste: Sport extra"]

    assert await _summaries(hass, "calendar.t") == by_title
    assert await _summaries(hass, "calendar.c") == by_category

    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    assert await _summaries(hass, "calendar.t") == by_title
    assert await _summaries(hass, "calendar.c") == by_category


def test_weekday_vocabulary_matches_home_assistant() -> None:
    assert tuple(HA_WEEKDAYS) == settings.WEEKDAYS
