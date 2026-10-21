"""Past matches stay in the calendar for its retention days after the feed drops them (EVT-07, D-14..D-19)."""

from datetime import datetime
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


F1_3 = (("F1", {"channels": ["daserste.de"], "retention_days": 3}),)
RACE_STOP = "2026-10-13T11:30:00+00:00"


async def _stored(hass_storage: dict[str, Any], entry: MockConfigEntry, *, flush: bool = True) -> dict[str, Any]:
    """Return the only calendar's stored record, flushing the match store first unless told not to."""
    from custom_components.xmltv_calendar.cache import cache_key

    if flush:
        await entry.runtime_data.match_store.async_flush()
    calendars = hass_storage[f"xmltv_calendar.matches.{cache_key(entry)}"]["data"]["calendars"]
    (record,) = calendars.values()
    return record


def _retained_titles(record: dict[str, Any]) -> list[str]:
    return [item["titles"][0] for item in record["retained"]]


async def _retain_race(
    hass: HomeAssistant,
    freezer: Any,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    calendars: Any = F1,
) -> MockConfigEntry:
    """Set up at NOW, then at 12:00Z refresh with a feed without the ended race, so the race is retained."""
    freezer.move_to(NOW)
    entry = await setup_xmltv(_variant(0), calendars=calendars)
    freezer.move_to("2026-10-13T12:00:00+00:00")
    await _refresh(hass, aioclient_mock, entry, _variant(1, BASIC_FEED, RACE_MARKER))
    assert RACE_SUMMARY in await _summaries(hass)
    return entry


async def test_three_day_retention_survives_parser_cutoff(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(_variant(0), calendars=F1_3)
    # Unchanged feeds keep the same data object: no refilter until 2026-10-15
    for when in ("2026-10-14T06:00:00+00:00", "2026-10-15T06:00:00+00:00"):
        freezer.move_to(when)
        await _refresh(hass, aioclient_mock, entry, _variant(0))

    # Two days after the end the parser no longer keeps the race; only the previous run's matches hold it
    freezer.move_to("2026-10-15T12:00:00+00:00")
    await _refresh(hass, aioclient_mock, entry, _variant(1, BASIC_FEED, RACE_MARKER))
    assert RACE_SUMMARY in await _summaries(hass)

    freezer.move_to("2026-10-16T12:00:00+00:00")
    await _refresh(hass, aioclient_mock, entry, _variant(2, BASIC_FEED, RACE_MARKER))
    assert RACE_SUMMARY not in await _summaries(hass)


async def test_capture_on_reload(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(_variant(0), calendars=F1_3)

    # No refilter since the race ended; the reload parses the cached feed without the race (one-day cut-off)
    freezer.move_to("2026-10-15T12:00:00+00:00")
    await _reload(hass, entry)
    assert RACE_SUMMARY in await _summaries(hass)


async def test_capture_on_stop(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    hass_storage: dict[str, Any],
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    from homeassistant.const import EVENT_HOMEASSISTANT_FINAL_WRITE, EVENT_HOMEASSISTANT_STOP

    freezer.move_to(NOW)
    entry = await setup_xmltv(_variant(0), calendars=F1_3)
    freezer.move_to("2026-10-13T12:00:00+00:00")

    hass.bus.async_fire(EVENT_HOMEASSISTANT_STOP)
    await hass.async_block_till_done()
    hass.bus.async_fire(EVENT_HOMEASSISTANT_FINAL_WRITE)
    await hass.async_block_till_done()

    record = await _stored(hass_storage, entry, flush=False)
    assert _retained_titles(record) == ["Formel 1: Großer Preis von Mexiko"]


async def test_retention_zero_keeps_nothing(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    aioclient_mock: AiohttpClientMocker,
    hass_storage: dict[str, Any],
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(_variant(0), calendars=(("F1", {"channels": ["daserste.de"], "retention_days": 0}),))
    freezer.move_to("2026-10-13T12:00:00+00:00")
    # Still in the feed: a feed match, shown whatever the retention
    await _refresh(hass, aioclient_mock, entry, _variant(1))
    assert RACE_SUMMARY in await _summaries(hass)

    await _refresh(hass, aioclient_mock, entry, _variant(2, BASIC_FEED, RACE_MARKER))
    assert RACE_SUMMARY not in await _summaries(hass)
    assert (await _stored(hass_storage, entry))["retained"] == []


async def test_filter_edit_rechecks_retained(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    aioclient_mock: AiohttpClientMocker,
    hass_storage: dict[str, Any],
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await _retain_race(hass, freezer, aioclient_mock, setup_xmltv)
    (subentry_id,) = entry.subentries

    assert hass.config_entries.async_update_subentry(
        entry, entry.subentries[subentry_id], data={"channels": ["zdf.de"]}
    )
    await hass.async_block_till_done(wait_background_tasks=True)
    assert RACE_SUMMARY not in await _summaries(hass)
    assert "Formel 1: Großer Preis von Mexiko" not in _retained_titles(await _stored(hass_storage, entry))

    # A widened filter cannot bring back what was dropped (D-17)
    assert hass.config_entries.async_update_subentry(
        entry, entry.subentries[subentry_id], data={"channels": ["daserste.de"]}
    )
    await hass.async_block_till_done(wait_background_tasks=True)
    assert RACE_SUMMARY not in await _summaries(hass)


async def test_template_edit_changes_retained_text(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await _retain_race(hass, freezer, aioclient_mock, setup_xmltv)
    (subentry_id,) = entry.subentries

    assert hass.config_entries.async_update_subentry(
        entry, entry.subentries[subentry_id], data={"channels": ["daserste.de"], "title_template": "{title}"}
    )
    await hass.async_block_till_done(wait_background_tasks=True)
    assert "Formel 1: Großer Preis von Mexiko" in await _summaries(hass)


async def test_retention_edit_applies_in_place(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await _retain_race(hass, freezer, aioclient_mock, setup_xmltv)
    (subentry_id,) = entry.subentries
    requests = aioclient_mock.call_count

    assert hass.config_entries.async_update_subentry(
        entry, entry.subentries[subentry_id], data={"channels": ["daserste.de"], "retention_days": 0}
    )
    await hass.async_block_till_done(wait_background_tasks=True)

    assert RACE_SUMMARY not in await _summaries(hass)
    assert entry.state is ConfigEntryState.LOADED
    assert aioclient_mock.call_count == requests


async def test_timezone_change_drops_retained(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    aioclient_mock: AiohttpClientMocker,
    hass_storage: dict[str, Any],
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    from custom_components.xmltv_calendar.cache import cache_key

    entry = await _retain_race(hass, freezer, aioclient_mock, setup_xmltv)
    seen = set((await _stored(hass_storage, entry))["seen"])
    assert seen

    # Retained programmes carry times shifted by the old correction: dropped, the seen-set stays (Open Question 2)
    hass.config_entries.async_update_entry(entry, options={**entry.options, "offset_minutes": 30})
    await hass.async_block_till_done(wait_background_tasks=True)
    assert entry.state is ConfigEntryState.LOADED

    assert RACE_SUMMARY not in await _summaries(hass)
    record = await _stored(hass_storage, entry)
    assert record["retained"] == []
    assert seen <= set(record["seen"])
    stored = hass_storage[f"xmltv_calendar.matches.{cache_key(entry)}"]["data"]
    assert stored["source"] == {"naive_timezone": "utc", "offset_minutes": 30}


async def test_no_uid_is_shown_twice(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    aioclient_mock: AiohttpClientMocker,
    hass_storage: dict[str, Any],
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    from custom_components.xmltv_calendar.xmltv.render import event_uid

    freezer.move_to(NOW)
    entry = await setup_xmltv(_variant(0), calendars=(("All", {}),))
    # 12:00Z: the race ended and is still in the feed (feed match and retained); ZDF's first heute ended and was dropped
    freezer.move_to("2026-10-13T12:00:00+00:00")
    zdf_noon = b'<programme channel="zdf.de" start="20261013120000 +0200"'
    await _refresh(hass, aioclient_mock, entry, _variant(1, BASIC_FEED, zdf_noon))

    # The service response carries no UID: read the entity's events directly
    entity = entry.runtime_data.calendars[next(iter(entry.subentries))]
    events = await entity.async_get_events(
        hass,
        datetime.fromisoformat("2026-10-12T00:00:00+00:00"),
        datetime.fromisoformat("2026-10-17T00:00:00+00:00"),
    )
    uids = [event.uid for event in events]
    assert len(uids) == len(set(uids))

    feed_uids = {event_uid(programme) for programme in entity._feed_matches}
    retained_uids = {event_uid(programme) for programme in entity._retained_shown}
    assert feed_uids.isdisjoint(retained_uids)
    assert set(uids) <= feed_uids | retained_uids
    summaries = [event.summary for event in events]
    assert "Das Erste: Formel 1: Großer Preis von Mexiko" in summaries
    assert summaries.count("ZDF: heute") == 2  # the dropped one is retained
    assert "Formel 1: Großer Preis von Mexiko" in _retained_titles(await _stored(hass_storage, entry))


async def test_expired_retained_hidden_without_refilter(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await _retain_race(hass, freezer, aioclient_mock, setup_xmltv)
    coordinator = entry.runtime_data.coordinator
    data = coordinator.data

    # The source answers 304 from now on: the data object stays, no refilter runs
    aioclient_mock.clear_requests()
    aioclient_mock.get(FEED_URL, status=304)
    freezer.move_to("2026-10-14T11:00:00+00:00")
    await coordinator.async_refresh()
    await hass.async_block_till_done(wait_background_tasks=True)
    assert RACE_SUMMARY in await _summaries(hass)

    # One hour after the one-day window ended (11:30Z)
    freezer.move_to("2026-10-14T12:30:00+00:00")
    await coordinator.async_refresh()
    await hass.async_block_till_done(wait_background_tasks=True)
    assert coordinator.data is data
    assert RACE_SUMMARY not in await _summaries(hass)
