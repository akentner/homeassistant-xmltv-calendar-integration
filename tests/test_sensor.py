"""Next-match sensor: one timestamp sensor per calendar showing the start of the next match (AUT-03, D-01..D-06)."""

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from homeassistant.helpers import entity_registry as er

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant

BASIC_FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()
F1 = (("F1", {"channels": ["daserste.de"]}),)
SENSOR = "sensor.f1_next_programme"
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
