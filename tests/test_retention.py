"""Past matches stay in the calendar for its retention days after the feed drops them (EVT-07, D-14..D-19)."""

from pathlib import Path
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntryState

from .conftest import FEED_URL

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

BASIC_FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()
NOW = "2026-10-13T06:00:00+00:00"
F1 = (("F1", {"channels": ["daserste.de"]}),)
ENTITY = "calendar.f1"

# The basic feed's race ends 2026-10-13 11:30Z; Tagesschau starts 18:00Z
RACE_MARKER = b'<programme channel="daserste.de" start="20261013120000 +0200"'
TAGESSCHAU_MARKER = b'<programme channel="daserste.de" start="20261013200000 +0200"'
RACE_SUMMARY = "Das Erste: Formel 1: Großer Preis von Mexiko"
TAGESSCHAU_SUMMARY = "Das Erste: Tagesschau"


def _without(feed: bytes, marker: bytes) -> bytes:
    """Return `feed` without the programme element that starts with `marker`."""
    head, rest = feed.split(marker, 1)
    _, tail = rest.split(b"</programme>", 1)
    return head + tail


def _later(n: int) -> bytes:
    """Return a ZDF programme on 2026-10-16 that keeps the feed current; `n` makes every variant's body unique."""
    return (
        f'<programme channel="zdf.de" start="20261016{n:02d}0000 +0200" stop="20261016{n:02d}3000 +0200">'
        f"<title>Later {n}</title></programme>"
    ).encode()


def _variant(n: int, feed: bytes = BASIC_FEED, *drop: bytes) -> bytes:
    """Return `feed` without the programmes of `drop` and with a unique later programme, so every refresh refilters."""
    for marker in drop:
        feed = _without(feed, marker)
    return feed.replace(b"</tv>", _later(n) + b"\n</tv>")


async def _refresh(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, entry: MockConfigEntry, feed: bytes
) -> None:
    """Serve `feed` and run one coordinator refresh, waiting for the calendars to refilter."""
    aioclient_mock.clear_requests()
    aioclient_mock.get(FEED_URL, content=feed)
    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done(wait_background_tasks=True)


async def _reload(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert entry.state is ConfigEntryState.LOADED


async def _events(hass: HomeAssistant, entity_id: str = ENTITY) -> list[dict[str, Any]]:
    response = await hass.services.async_call(
        "calendar",
        "get_events",
        {"entity_id": entity_id, "start_date_time": "2026-10-12T00:00:00+00:00", "duration": {"days": 5}},
        blocking=True,
        return_response=True,
    )
    return response[entity_id]["events"]


async def _summaries(hass: HomeAssistant, entity_id: str = ENTITY) -> list[str]:
    return [event["summary"] for event in await _events(hass, entity_id)]


async def test_dropped_match_stays_for_retention_days(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(BASIC_FEED, calendars=F1)
    assert RACE_SUMMARY in await _summaries(hass)

    # The race ended at 11:30Z; the next feed no longer lists it
    freezer.move_to("2026-10-13T12:00:00+00:00")
    await _refresh(hass, aioclient_mock, entry, _variant(1, BASIC_FEED, RACE_MARKER))
    assert RACE_SUMMARY in await _summaries(hass)

    await _reload(hass, entry)
    assert RACE_SUMMARY in await _summaries(hass)

    # 23.5 h after the end: still inside the default one-day window
    freezer.move_to("2026-10-14T11:00:00+00:00")
    await _refresh(hass, aioclient_mock, entry, _variant(2, BASIC_FEED, RACE_MARKER))
    assert RACE_SUMMARY in await _summaries(hass)

    # 24.5 h after the end: gone
    freezer.move_to("2026-10-14T12:00:00+00:00")
    await _refresh(hass, aioclient_mock, entry, _variant(3, BASIC_FEED, RACE_MARKER))
    assert RACE_SUMMARY not in await _summaries(hass)


async def test_future_match_removed_from_feed_disappears(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(BASIC_FEED, calendars=F1)
    assert TAGESSCHAU_SUMMARY in await _summaries(hass)

    # Tagesschau has not started: the feed is the truth about the future (D-16)
    await _refresh(hass, aioclient_mock, entry, _variant(1, BASIC_FEED, TAGESSCHAU_MARKER))
    assert TAGESSCHAU_SUMMARY not in await _summaries(hass)
