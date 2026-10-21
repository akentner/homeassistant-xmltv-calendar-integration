"""New-match event: one xmltv_calendar_new_match event per newly published matching programme (EVT-08, D-07..D-13)."""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pytest_homeassistant_custom_component.common import async_capture_events

from .conftest import FEED_URL

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    import pytest
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

BASIC_FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()
EVENT = "xmltv_calendar_new_match"
NOW = "2026-10-13T06:00:00+00:00"
TEST_CALENDAR = (("Test", {}),)


def _programme_xml(channel: str, start: str, stop: str, title: str) -> bytes:
    """Return one programme element; start and stop are XMLTV times like '20261014160000 +0200'."""
    return f'<programme channel="{channel}" start="{start}" stop="{stop}"><title>{title}</title></programme>'.encode()


def _with(*programmes: bytes) -> bytes:
    """Return the basic feed with `programmes` appended."""
    return BASIC_FEED.replace(b"</tv>", b"".join(programmes) + b"\n</tv>")


RACE_XML = _programme_xml("daserste.de", "20261014160000 +0200", "20261014180000 +0200", "Formel 1: Rennen")


def _race() -> Any:
    from custom_components.xmltv_calendar.xmltv.model import Programme

    return Programme(
        channel_id="daserste.de",
        start=datetime.fromisoformat("2026-10-14T16:00:00+02:00"),
        stop=datetime.fromisoformat("2026-10-14T18:00:00+02:00"),
        titles=("Formel 1: Rennen",),
        sub_titles=(),
        description=None,
        categories=(),
        episode=None,
    )


async def _refresh(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, entry: MockConfigEntry, feed: bytes
) -> None:
    """Serve `feed` and run one coordinator refresh, waiting for the calendars to refilter."""
    aioclient_mock.clear_requests()
    aioclient_mock.get(FEED_URL, content=feed)
    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done(wait_background_tasks=True)


async def _stored_seen(
    hass_storage: dict[str, Any], entry: MockConfigEntry, subentry_id: str | None = None
) -> dict[str, int]:
    """Flush the match store and return one calendar's stored seen-set (the only calendar when not given)."""
    from custom_components.xmltv_calendar.cache import cache_key

    await entry.runtime_data.match_store.async_flush()
    calendars = hass_storage[f"xmltv_calendar.matches.{cache_key(entry)}"]["data"]["calendars"]
    if subentry_id is None:
        (subentry_id,) = calendars
    return calendars[subentry_id]["seen"]


async def test_new_programme_fires_one_event(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    from custom_components.xmltv_calendar.xmltv import render

    freezer.move_to(NOW)
    events = async_capture_events(hass, EVENT)
    entry = await setup_xmltv(BASIC_FEED, calendars=TEST_CALENDAR)
    assert events == []

    await _refresh(hass, aioclient_mock, entry, _with(RACE_XML))

    assert [event.data for event in events] == [
        {
            "entity_id": "calendar.test",
            "calendar": "Test",
            "title": "Formel 1: Rennen",
            "summary": "Das Erste: Formel 1: Rennen",
            "channel": "Das Erste",
            "channel_id": "daserste.de",
            "start": "2026-10-14T16:00:00+02:00",
            "end": "2026-10-14T18:00:00+02:00",
            "uid": render.event_uid(_race()),
        }
    ]


async def test_seen_set_is_persisted(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    aioclient_mock: AiohttpClientMocker,
    hass_storage: dict[str, Any],
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    from custom_components.xmltv_calendar.cache import cache_key
    from custom_components.xmltv_calendar.xmltv import render

    freezer.move_to(NOW)
    entry = await setup_xmltv(BASIC_FEED, calendars=TEST_CALENDAR)
    (subentry_id,) = entry.subentries
    await _refresh(hass, aioclient_mock, entry, _with(RACE_XML))
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    race = _race()
    seen = hass_storage[f"xmltv_calendar.matches.{cache_key(entry)}"]["data"]["calendars"][subentry_id]["seen"]
    assert seen[render.event_uid(race)] == int(race.stop.timestamp())


def _show_feed(count: int) -> bytes:
    """Return the basic feed plus `count` ten-minute ZDF shows from 2026-10-14 00:00 +0200 on."""
    first = datetime.fromisoformat("2026-10-14T00:00:00+02:00")
    shows = []
    for i in range(count):
        start = first + timedelta(minutes=10 * i)
        stop = start + timedelta(minutes=10)
        shows.append(_programme_xml("zdf.de", f"{start:%Y%m%d%H%M%S %z}", f"{stop:%Y%m%d%H%M%S %z}", f"Show {i:02d}"))
    return _with(*shows)


async def test_burst_is_capped(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    aioclient_mock: AiohttpClientMocker,
    caplog: pytest.LogCaptureFixture,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    freezer.move_to(NOW)
    events = async_capture_events(hass, EVENT)
    entry = await setup_xmltv(BASIC_FEED, calendars=TEST_CALENDAR)
    feed = _show_feed(60)

    with caplog.at_level(logging.WARNING):
        await _refresh(hass, aioclient_mock, entry, feed)

    # The 50 earliest are announced in start order (D-12)
    assert [event.data["title"] for event in events] == [f"Show {i:02d}" for i in range(50)]
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING and "not announced" in r.message]
    assert warnings == ["Calendar calendar.test: 10 new matches not announced (limit 50 per refresh)"]

    # The 10 suppressed ones joined the seen-set: the same feed announces nothing again
    await _refresh(hass, aioclient_mock, entry, feed)
    assert len(events) == 50


async def test_started_match_is_not_announced(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    aioclient_mock: AiohttpClientMocker,
    hass_storage: dict[str, Any],
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    freezer.move_to(NOW)
    events = async_capture_events(hass, EVENT)
    entry = await setup_xmltv(BASIC_FEED, calendars=TEST_CALENDAR)
    # 07:30-09:00 +0200 is airing at 06:00Z (08:00 Berlin)
    airing = _programme_xml("zdf.de", "20261013073000 +0200", "20261013090000 +0200", "Morgenmagazin")
    await _refresh(hass, aioclient_mock, entry, _with(airing))

    assert events == []
    seen = await _stored_seen(hass_storage, entry)
    stop = datetime.fromisoformat("2026-10-13T09:00:00+02:00")
    uids = [uid for uid in seen if uid.startswith("zdf.de-20261013T053000Z-")]
    assert len(uids) == 1
    assert seen[uids[0]] == int(stop.timestamp())


async def test_seen_is_pruned_after_the_window(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    aioclient_mock: AiohttpClientMocker,
    hass_storage: dict[str, Any],
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(BASIC_FEED, calendars=TEST_CALENDAR)
    first_day = set(await _stored_seen(hass_storage, entry))
    assert first_day  # the basic feed's 13 October programmes

    # Three days later every 13 October programme ended more than one day ago; the feed rolled forward
    later = _programme_xml("zdf.de", "20261016200000 +0200", "20261016210000 +0200", "heute-show")
    rolled = BASIC_FEED.split(b"<programme", 1)[0] + later + b"\n</tv>"
    aioclient_mock.clear_requests()
    aioclient_mock.get(FEED_URL, content=rolled)
    freezer.move_to("2026-10-16T06:00:00+00:00")
    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done(wait_background_tasks=True)

    seen = await _stored_seen(hass_storage, entry)
    assert first_day.isdisjoint(seen)
    assert len(seen) == 1
