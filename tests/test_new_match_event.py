"""New-match event: one xmltv_calendar_new_match event per newly published matching programme (EVT-08, D-07..D-13)."""

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pytest_homeassistant_custom_component.common import async_capture_events

from .conftest import FEED_URL

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

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
