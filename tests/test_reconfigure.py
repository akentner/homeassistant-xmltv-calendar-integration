"""Calendar subentry edits apply in place: no download, no parse, no reload, siblings untouched (FLT-11, D-04)."""

import logging
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr

from custom_components.xmltv_calendar.calendar import XmltvCalendarEntity

from .conftest import DOMAIN

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    import pytest
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()
NOW = "2026-10-13T06:00:00+00:00"


def _subentry_id(entry: MockConfigEntry, title: str) -> str:
    (subentry_id,) = [sid for sid, sub in entry.subentries.items() if sub.title == title]
    return subentry_id


def _suggested(result: Any, name: str) -> Any:
    """Return the suggested value of a form field, or None when the field has none."""
    for key in result["data_schema"].schema:
        if key == name:
            return (key.description or {}).get("suggested_value")
    msg = f"{name} not in form"
    raise AssertionError(msg)


async def _summaries(hass: HomeAssistant, entity_id: str) -> list[str]:
    response = await hass.services.async_call(
        "calendar",
        "get_events",
        {"entity_id": entity_id, "start_date_time": "2026-10-13T00:00:00+00:00", "duration": {"hours": 24}},
        blocking=True,
        return_response=True,
    )
    return [event["summary"] for event in response[entity_id]["events"]]


async def test_data_change_applies_in_place(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(FEED, calendars=(("A", {"include": "tagesschau"}), ("B", {"channels": ["zdf.de"]})))
    a_id = _subentry_id(entry, "A")
    b_id = _subentry_id(entry, "B")
    calls = aioclient_mock.call_count
    runtime = entry.runtime_data
    epg = runtime.coordinator.data
    entity_b = runtime.calendars[b_id]
    b_events = await _summaries(hass, "calendar.b")

    assert hass.config_entries.async_update_subentry(entry, entry.subentries[a_id], data={"include": "formel"})
    await hass.async_block_till_done()

    assert await _summaries(hass, "calendar.a") == ["Das Erste: Formel 1: Großer Preis von Mexiko"]
    assert aioclient_mock.call_count == calls
    assert entry.runtime_data is runtime
    assert runtime.coordinator.data is epg
    assert runtime.calendars[b_id] is entity_b
    assert await _summaries(hass, "calendar.b") == b_events


async def test_title_change_renames_device(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(FEED, calendars=(("A", {"include": "tagesschau"}),))
    a_id = _subentry_id(entry, "A")
    calls = aioclient_mock.call_count
    index = entry.runtime_data.calendars[a_id]._index

    assert hass.config_entries.async_update_subentry(entry, entry.subentries[a_id], title="Renamed")
    await hass.async_block_till_done()

    device = dr.async_get(hass).async_get_device_by_identifier((DOMAIN, a_id), entry.entry_id)
    assert device is not None
    assert device.name == "Renamed"
    state = hass.states.get("calendar.a")
    assert state is not None
    assert state.attributes["friendly_name"] == "Renamed"
    assert hass.states.get("calendar.renamed") is None
    assert entry.runtime_data.calendars[a_id]._index is index
    assert aioclient_mock.call_count == calls


async def test_unchanged_update_is_a_no_op(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(FEED, calendars=(("A", {"include": "tagesschau"}),))
    a_id = _subentry_id(entry, "A")
    index = entry.runtime_data.calendars[a_id]._index

    assert not hass.config_entries.async_update_subentry(
        entry, entry.subentries[a_id], title="A", data={"include": "tagesschau"}
    )
    await hass.async_block_till_done()

    assert entry.runtime_data.calendars[a_id]._index is index


async def test_two_calendars_changed_together(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(FEED, calendars=(("A", {"include": "tagesschau"}), ("B", {"channels": ["zdf.de"]})))
    a_id = _subentry_id(entry, "A")
    b_id = _subentry_id(entry, "B")

    hass.config_entries.async_update_subentry(entry, entry.subentries[a_id], data={"include": "formel"})
    hass.config_entries.async_update_subentry(entry, entry.subentries[b_id], data={"channels": ["daserste.de"]})
    await hass.async_block_till_done()

    assert await _summaries(hass, "calendar.a") == ["Das Erste: Formel 1: Großer Preis von Mexiko"]
    assert await _summaries(hass, "calendar.b") == [
        "Das Erste: Formel 1: Großer Preis von Mexiko",
        "Das Erste: Tagesschau",
    ]


async def test_last_of_two_updates_wins(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(FEED, calendars=(("A", {"include": "tagesschau"}),))
    a_id = _subentry_id(entry, "A")

    hass.config_entries.async_update_subentry(entry, entry.subentries[a_id], data={"include": "formel"})
    hass.config_entries.async_update_subentry(
        entry, entry.subentries[a_id], data={"include": "heute", "channels": ["zdf.de"]}
    )
    await hass.async_block_till_done()

    assert await _summaries(hass, "calendar.a") == ["ZDF: heute", "ZDF: heute"]


async def test_apply_before_added_stores_settings(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED, calendars=(("A", {"include": "tagesschau"}),))
    subentry = entry.subentries[_subentry_id(entry, "A")]
    entity = XmltvCalendarEntity(entry.runtime_data.coordinator, entry, subentry)
    assert entity.hass is None

    hass.config_entries.async_update_subentry(entry, subentry, data={"include": "formel"})
    await entity.async_apply_subentry(subentry)

    assert entity._spec is not None
    assert [pattern.pattern for pattern in entity._spec.include] == ["formel"]
    assert not entity.differs_from(subentry)


async def test_corrupt_pattern_keeps_previous_matches(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
    caplog: pytest.LogCaptureFixture,
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(FEED, calendars=(("A", {"include": "tagesschau"}), ("B", {"channels": ["zdf.de"]})))
    a_id = _subentry_id(entry, "A")
    b_id = _subentry_id(entry, "B")
    a_events = await _summaries(hass, "calendar.a")
    assert a_events == ["Das Erste: Tagesschau"]

    # Hand-edited storage: A's pattern bypasses the flow's validation; B's edit fires the one listener call
    object.__setattr__(entry.subentries[a_id], "data", MappingProxyType({"include": "("}))
    assert hass.config_entries.async_update_subentry(entry, entry.subentries[b_id], data={"channels": ["daserste.de"]})
    await hass.async_block_till_done()

    assert await _summaries(hass, "calendar.a") == a_events
    warnings = [
        r
        for r in caplog.records
        if r.levelno == logging.WARNING and "stored filter pattern" in r.getMessage() and "calendar.a" in r.getMessage()
    ]
    assert len(warnings) == 1
    assert await _summaries(hass, "calendar.b") == [
        "Das Erste: Formel 1: Großer Preis von Mexiko",
        "Das Erste: Tagesschau",
    ]


async def test_reconfigure_flow_end_to_end(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(FEED, calendars=(("A", {"include": "tagesschau"}), ("B", {"channels": ["zdf.de"]})))
    a_id = _subentry_id(entry, "A")
    b_id = _subentry_id(entry, "B")
    calls = aioclient_mock.call_count
    runtime = entry.runtime_data
    epg = runtime.coordinator.data
    entity_b = runtime.calendars[b_id]
    b_events = await _summaries(hass, "calendar.b")

    # The frontend offers "Edit calendar" only when the flow class has a reconfigure step
    assert entry.supported_subentry_types["calendar"]["supports_reconfigure"] is True

    result = await entry.start_subentry_reconfigure_flow(hass, a_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "basic"
    assert _suggested(result, "name") == "A"
    assert _suggested(result, "include") == "tagesschau"

    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {"name": "A", "include": "formel"})
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "preview"
    assert result["description_placeholders"]["count"] == "1"

    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {"next_step_id": "save"})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()

    assert await _summaries(hass, "calendar.a") == ["Das Erste: Formel 1: Großer Preis von Mexiko"]
    assert aioclient_mock.call_count == calls
    assert entry.runtime_data is runtime
    assert runtime.coordinator.data is epg
    assert runtime.calendars[b_id] is entity_b
    assert await _summaries(hass, "calendar.b") == b_events
