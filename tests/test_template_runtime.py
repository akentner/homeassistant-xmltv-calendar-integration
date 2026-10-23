"""Runtime behavior of templates on the Home Assistant surfaces: local time, fallbacks and side effects (D-03, D-05)."""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from homeassistant.components.calendar.const import DATA_COMPONENT
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from pytest_homeassistant_custom_component.common import async_capture_events

from custom_components.xmltv_calendar.matcher import signal_matches

from .test_new_match_event import (
    BASIC_FEED,
    EVENT,
    F1_ONLY,
    NOW,
    RACE_XML,
    _programme_xml,
    _refresh,
    _stored_seen,
    _with,
)
from .test_sensor import SENSOR

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    import pytest
    from homeassistant.components.calendar import CalendarEvent
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

CHANNELS = (
    b'<?xml version="1.0" encoding="UTF-8"?>\n<tv>\n'
    b'<channel id="daserste.de"><display-name>Das Erste</display-name></channel>\n'
)
# A UTC feed: the wall time in Europe/Berlin (+02:00 in October) differs from the offset written in the feed
LIVE_UTC = _programme_xml("daserste.de", "20261013050000 +0000", "20261013070000 +0000", "Live")
NEXT_UTC = _programme_xml("daserste.de", "20261013100000 +0000", "20261013113000 +0000", "Spaeter")
NEW_UTC = _programme_xml("daserste.de", "20261014120000 +0000", "20261014133000 +0000", "Neu")
UTC_FEED = CHANNELS + LIVE_UTC + NEXT_UTC + b"\n</tv>"
LOCAL_START = "{{ title }} @ {{ start }}"
LOCAL_END = "until {{ end }}"
LOCAL_CALENDAR = (
    ("F1", {"channels": ["daserste.de"], "title_template": LOCAL_START, "description_template": LOCAL_END}),
)


async def _get_events(hass: HomeAssistant, entity_id: str) -> list[dict[str, Any]]:
    response = await hass.services.async_call(
        "calendar",
        "get_events",
        {"entity_id": entity_id, "start_date_time": "2026-10-12T00:00:00+00:00", "duration": {"hours": 72}},
        blocking=True,
        return_response=True,
    )
    return response[entity_id]["events"]


async def test_start_variable_is_local_time_everywhere(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    freezer.move_to(NOW)
    events = async_capture_events(hass, EVENT)
    entry = await setup_xmltv(UTC_FEED, calendars=LOCAL_CALENDAR)

    # get_events: 10:00 UTC is 12:00 in Berlin, with the +02:00 offset instead of the feed's +00:00
    listed = await _get_events(hass, "calendar.f1")
    assert [event["summary"] for event in listed] == [
        "Live @ 2026-10-13 07:00:00+02:00",
        "Spaeter @ 2026-10-13 12:00:00+02:00",
    ]
    assert [event["description"] for event in listed] == [
        "until 2026-10-13 09:00:00+02:00",
        "until 2026-10-13 13:30:00+02:00",
    ]
    # The live event of the calendar entity (Live is airing at 06:00 UTC)
    assert hass.states.get("calendar.f1").attributes["message"] == "Live @ 2026-10-13 07:00:00+02:00"
    # The next-match sensor summary
    assert hass.states.get(SENSOR).attributes["summary"] == "Spaeter @ 2026-10-13 12:00:00+02:00"

    # The summary of the new-match event fired by a refresh that adds a UTC programme
    await _refresh(hass, aioclient_mock, entry, CHANNELS + LIVE_UTC + NEXT_UTC + NEW_UTC + b"\n</tv>")
    assert [event.data["summary"] for event in events] == ["Neu @ 2026-10-14 14:00:00+02:00"]
    assert events[0].data["start"] == "2026-10-14T14:00:00+02:00"


RENDER_LOGGER = "custom_components.xmltv_calendar.xmltv.render"


async def _entity_events(hass: HomeAssistant, entity_id: str) -> list[CalendarEvent]:
    """Return the entity's events with their UIDs, which the get_events service response leaves out."""
    entity = hass.data[DATA_COMPONENT].get_entity(entity_id)
    assert entity is not None
    return await entity.async_get_events(
        hass, datetime.fromisoformat("2026-10-12T00:00:00+00:00"), datetime.fromisoformat("2026-10-15T00:00:00+00:00")
    )


def _render_warnings(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [
        record.getMessage()
        for record in caplog.records
        if record.name == RENDER_LOGGER and record.levelno >= logging.WARNING
    ]


def _edit(hass: HomeAssistant, entry: MockConfigEntry, data: dict[str, Any]) -> None:
    """Replace the data of the only calendar subentry, bypassing the flow like a hand edit of the storage."""
    (subentry,) = entry.subentries.values()
    assert hass.config_entries.async_update_subentry(entry, subentry, data=data)


async def test_runtime_failure_warns_once_per_calendar(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    caplog: pytest.LogCaptureFixture,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(BASIC_FEED, calendars=F1_ONLY)
    caplog.clear()

    # Compiles, but raises when rendered
    _edit(
        hass,
        entry,
        {"channels": ["daserste.de"], "title_template": "{{ 1 / 0 }}", "description_template": "{{ 1 / 0 }}"},
    )
    await hass.async_block_till_done()

    first = await _get_events(hass, "calendar.f1")
    second = await _get_events(hass, "calendar.f1")

    # Every programme is still returned: plain title as summary, default description
    assert [event["summary"] for event in first] == ["Formel 1: Großer Preis von Mexiko", "Tagesschau"]
    assert [event.get("description") for event in first] == ["Qualifying", None]
    assert second == first
    warnings = _render_warnings(caplog)
    assert len(warnings) == 1
    assert "F1" in warnings[0]
    assert "ZeroDivisionError" in warnings[0]
    assert "Formel" not in warnings[0]
    assert "Tagesschau" not in warnings[0]


async def test_template_edit_does_not_reannounce_matches(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    aioclient_mock: AiohttpClientMocker,
    hass_storage: dict[str, Any],
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    freezer.move_to(NOW)
    events = async_capture_events(hass, EVENT)
    entry = await setup_xmltv(BASIC_FEED, calendars=F1_ONLY)
    await _refresh(hass, aioclient_mock, entry, _with(RACE_XML))
    assert [event.data["title"] for event in events] == ["Formel 1: Rennen"]
    before = await _entity_events(hass, "calendar.f1")
    seen = await _stored_seen(hass_storage, entry)

    _edit(hass, entry, {"channels": ["daserste.de"], "title_template": "{{ title | upper }}"})
    await hass.async_block_till_done(wait_background_tasks=True)

    after = await _entity_events(hass, "calendar.f1")
    assert len(events) == 1
    assert [event.uid for event in after] == [event.uid for event in before]
    assert [event.summary for event in after] == [
        "FORMEL 1: GROSSER PREIS VON MEXIKO",
        "TAGESSCHAU",
        "FORMEL 1: RENNEN",
    ]
    assert [event.summary for event in after] != [event.summary for event in before]
    assert await _stored_seen(hass_storage, entry) == seen


async def test_noop_data_change_sends_no_template_signal(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    freezer.move_to(NOW)
    data = {"channels": ["daserste.de"], "include": "Formel", "title_template": "{{ title }}"}
    entry = await setup_xmltv(BASIC_FEED, calendars=(("F1", data),))
    (subentry_id,) = entry.subentries
    signals: list[None] = []
    unsubscribe = async_dispatcher_connect(hass, signal_matches(subentry_id), lambda: signals.append(None))

    # Data differs, filter, templates and retention are equal
    _edit(hass, entry, {**data, "include": "Formel\n"})
    await hass.async_block_till_done(wait_background_tasks=True)
    assert signals == []

    _edit(hass, entry, {**data, "include": "Formel\n", "title_template": "{{ title | upper }}"})
    await hass.async_block_till_done(wait_background_tasks=True)
    assert len(signals) == 1
    unsubscribe()


async def test_stored_edit_to_legacy_text_warns_once_and_renders_default(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    caplog: pytest.LogCaptureFixture,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(BASIC_FEED, calendars=F1_ONLY)
    caplog.clear()
    legacy = "{title} - {subtitle}"
    data = {"channels": ["daserste.de"], "title_template": legacy}

    _edit(hass, entry, data)
    await hass.async_block_till_done()

    assert [event["summary"] for event in await _get_events(hass, "calendar.f1")] == [
        "Das Erste: Formel 1: Großer Preis von Mexiko",
        "Das Erste: Tagesschau",
    ]
    warnings = _render_warnings(caplog)
    assert len(warnings) == 1
    assert "F1" in warnings[0]
    assert "legacy_placeholder" in warnings[0]
    assert legacy not in warnings[0]
    (subentry,) = entry.subentries.values()
    assert subentry.data["title_template"] == legacy

    # An unrelated listener call must not apply or log the same stored text again
    hass.config_entries.async_update_entry(entry, title="Source renamed")
    await hass.async_block_till_done()
    assert _render_warnings(caplog) == warnings
