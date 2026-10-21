"""Next-match sensor: one timestamp sensor per calendar showing the start of the next match (AUT-03, D-01..D-06)."""

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from .conftest import FEED_URL, complete_calendar_flow

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

BASIC_FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()
F1 = (("F1", {"channels": ["daserste.de"]}),)
SENSOR = "sensor.f1_next_programme"
# Formel 1: Rennen on Das Erste at 09:00 +0200, before every match of the basic feed
RACE = (
    b'<programme channel="daserste.de" start="20261013090000 +0200" stop="20261013110000 +0200">'
    b"<title>Formel 1: Rennen</title></programme>\n</tv>"
)
MATCH_KEYS = {"title", "summary", "channel", "channel_id", "start", "end", "subtitle", "episode", "description"}


async def test_next_match_sensor_shows_next_start(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    freezer.move_to("2026-10-13T06:00:00+00:00")
    await setup_xmltv(BASIC_FEED, calendars=F1)

    state = hass.states.get("sensor.f1_next_programme")
    assert state is not None
    # Formel 1 starts 12:00 +0200 on Das Erste
    assert state.state == "2026-10-13T10:00:00+00:00"


async def test_sensor_shares_the_calendar_device(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    freezer.move_to("2026-10-13T06:00:00+00:00")
    entry = await setup_xmltv(BASIC_FEED, calendars=F1)
    (subentry_id,) = entry.subentries

    registry = er.async_get(hass)
    sensor = registry.async_get("sensor.f1_next_programme")
    calendar = registry.async_get("calendar.f1")
    assert sensor is not None
    assert calendar is not None
    assert sensor.unique_id == f"{subentry_id}_next_match"
    assert sensor.device_id == calendar.device_id
    assert sensor.disabled_by is None


async def test_next_match_attributes(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    freezer.move_to("2026-10-13T06:00:00+00:00")
    await setup_xmltv(BASIC_FEED, calendars=F1)

    attributes = hass.states.get(SENSOR).attributes
    assert {key: attributes.get(key, "missing") for key in MATCH_KEYS} == {
        "title": "Formel 1: Großer Preis von Mexiko",
        "summary": "Das Erste: Formel 1: Großer Preis von Mexiko",
        "channel": "Das Erste",
        "channel_id": "daserste.de",
        "start": "2026-10-13T12:00:00+02:00",
        "end": "2026-10-13T13:30:00+02:00",
        "subtitle": "Qualifying",
        "episode": None,
        "description": None,
    }
    assert "uid" not in attributes


async def test_match_texts_are_not_recorded(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    freezer.move_to("2026-10-13T06:00:00+00:00")
    await setup_xmltv(BASIC_FEED, calendars=F1)

    state = hass.states.get(SENSOR)
    assert state.state_info is not None
    assert {"description", "subtitle", "episode"} <= state.state_info["unrecorded_attributes"]


async def test_airing_match_is_not_next(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    # The race airs 10:00-11:30 UTC; the next match that has not started is Tagesschau at 18:00 UTC (D-01)
    freezer.move_to("2026-10-13T10:30:00+00:00")
    await setup_xmltv(BASIC_FEED, calendars=F1)

    assert hass.states.get(SENSOR).state == "2026-10-13T18:00:00+00:00"


async def test_no_future_match_is_unknown_but_available(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    freezer.move_to("2026-10-13T19:00:00+00:00")
    await setup_xmltv(BASIC_FEED, calendars=(*F1, ("Absent", {"channels": ["absent.de"]})))

    for entity_id in (SENSOR, "sensor.absent_next_programme"):
        state = hass.states.get(entity_id)
        assert state is not None, entity_id
        assert state.state == "unknown", entity_id  # not "unavailable" (D-02)
        assert not MATCH_KEYS & set(state.attributes), entity_id


async def test_same_start_picks_feed_order(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    # Formel 1 (daserste.de) and heute (zdf.de) both start at 12:00 +0200
    freezer.move_to("2026-10-13T06:00:00+00:00")
    await setup_xmltv(BASIC_FEED, calendars=(("Test", {}),))

    state = hass.states.get("sensor.test_next_programme")
    assert state.state == "2026-10-13T10:00:00+00:00"
    assert state.attributes["channel_id"] == "daserste.de"


@pytest.mark.parametrize(
    ("language", "entity_id"),
    [("de", "sensor.formel_1_nachste_sendung"), ("en", "sensor.formel_1_next_programme")],
)
async def test_german_entity_ids(
    hass: HomeAssistant,
    freezer: Any,
    setup_xmltv: Callable[..., Awaitable[Any]],
    language: str,
    entity_id: str,
) -> None:
    freezer.move_to("2026-10-13T06:00:00+00:00")
    hass.config.language = language
    await setup_xmltv(BASIC_FEED, calendars=(("Formel 1", {"channels": ["daserste.de"]}),))

    assert hass.states.get(entity_id) is not None


async def _step_to(hass: HomeAssistant, freezer: Any, iso: str) -> None:
    freezer.move_to(iso)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def test_sensor_moves_on_at_match_start(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    freezer.move_to("2026-10-13T06:00:00+00:00")
    await setup_xmltv(BASIC_FEED, calendars=F1)
    calls = aioclient_mock.call_count
    assert hass.states.get(SENSOR).state == "2026-10-13T10:00:00+00:00"

    # At the race's start it no longer counts: the sensor moves on to Tagesschau without a refresh (D-06)
    await _step_to(hass, freezer, "2026-10-13T10:00:00+00:00")
    state = hass.states.get(SENSOR)
    assert state.state == "2026-10-13T18:00:00+00:00"
    assert state.attributes["title"] == "Tagesschau"
    assert aioclient_mock.call_count == calls


async def test_sensor_follows_new_feed_data(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    freezer.move_to("2026-10-13T06:00:00+00:00")
    entry = await setup_xmltv(BASIC_FEED, calendars=F1)
    assert hass.states.get(SENSOR).state == "2026-10-13T10:00:00+00:00"

    aioclient_mock.clear_requests()
    aioclient_mock.get(FEED_URL, content=BASIC_FEED.replace(b"</tv>", RACE))
    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get(SENSOR)
    assert state.state == "2026-10-13T07:00:00+00:00"
    assert state.attributes["title"] == "Formel 1: Rennen"


async def test_sensor_follows_filter_and_template_edits(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    freezer.move_to("2026-10-13T06:00:00+00:00")
    entry = await setup_xmltv(BASIC_FEED, calendars=F1)
    calls = aioclient_mock.call_count
    (subentry_id,) = entry.subentries

    # A filter edit is applied in place and refilters (D-04 of phase 2)
    assert hass.config_entries.async_update_subentry(
        entry, entry.subentries[subentry_id], data={"channels": ["zdf.de"]}
    )
    await hass.async_block_till_done()
    state = hass.states.get(SENSOR)
    assert state.state == "2026-10-13T10:00:00+00:00"
    assert state.attributes["channel_id"] == "zdf.de"
    assert state.attributes["summary"] == "ZDF: heute"

    # A template-only edit changes the summary without a refilter
    assert hass.config_entries.async_update_subentry(
        entry, entry.subentries[subentry_id], data={"channels": ["zdf.de"], "title_template": "{title}"}
    )
    await hass.async_block_till_done()
    assert hass.states.get(SENSOR).attributes["summary"] == "heute"

    assert entry.state is ConfigEntryState.LOADED
    assert aioclient_mock.call_count == calls


async def test_template_edit_with_invalid_pattern_reaches_sensor(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    freezer.move_to("2026-10-13T06:00:00+00:00")
    entry = await setup_xmltv(BASIC_FEED, calendars=F1)
    (subentry_id,) = entry.subentries
    assert hass.states.get(SENSOR).attributes["summary"] == "Das Erste: Formel 1: Großer Preis von Mexiko"

    # Stored data bypassing the flow: the pattern does not compile, so the calendar keeps its filter and matches
    # (T-02-01) and only the new template applies, without a refilter
    assert hass.config_entries.async_update_subentry(
        entry,
        entry.subentries[subentry_id],
        data={"channels": ["daserste.de"], "include": "(", "title_template": "{title}"},
    )
    await hass.async_block_till_done()

    state = hass.states.get(SENSOR)
    assert state.state == "2026-10-13T10:00:00+00:00"
    assert state.attributes["summary"] == "Formel 1: Großer Preis von Mexiko"


async def test_calendar_added_later_gets_a_sensor(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    freezer.move_to("2026-10-13T06:00:00+00:00")
    entry = await setup_xmltv(BASIC_FEED, calendars=F1)
    calls = aioclient_mock.call_count
    runtime = entry.runtime_data

    result = await complete_calendar_flow(hass, entry, {"name": "Late", "channels": ["zdf.de"]})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    state = hass.states.get("sensor.late_next_programme")
    assert state is not None
    assert state.state == "2026-10-13T10:00:00+00:00"
    assert state.attributes["channel_id"] == "zdf.de"
    assert entry.runtime_data is runtime  # no reload
    assert aioclient_mock.call_count == calls


async def test_invalid_stored_pattern_gives_unknown(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    freezer.move_to("2026-10-13T06:00:00+00:00")
    # Stored data bypassing the flow: "(" does not compile
    await setup_xmltv(BASIC_FEED, calendars=(("Broken", {"include": "("}), *F1))

    broken = hass.states.get("sensor.broken_next_programme")
    assert broken is not None
    assert broken.state == "unknown"
    assert not MATCH_KEYS & set(broken.attributes)
    assert hass.states.get(SENSOR).state == "2026-10-13T10:00:00+00:00"


async def test_sensor_unavailable_without_data(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    monkeypatch: pytest.MonkeyPatch,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    freezer.move_to("2026-10-13T06:00:00+00:00")
    entry = await setup_xmltv(BASIC_FEED, calendars=F1)
    coordinator = entry.runtime_data.coordinator

    monkeypatch.setattr(coordinator, "data", None)
    coordinator.async_update_listeners()
    await hass.async_block_till_done()

    assert hass.states.get(SENSOR).state == STATE_UNAVAILABLE
