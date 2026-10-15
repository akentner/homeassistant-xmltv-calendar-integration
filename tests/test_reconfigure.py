"""Calendar subentry edits apply in place: no download, no parse, no reload, siblings untouched (FLT-11, D-04)."""

import logging
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr

from custom_components.xmltv_calendar.calendar import XmltvCalendarEntity
from custom_components.xmltv_calendar.const import (
    CONF_ADVANCED,
    CONF_CHANNELS,
    CONF_NAME,
    CONF_TITLE_TEMPLATE,
    CONF_WEEKDAYS,
)
from custom_components.xmltv_calendar.xmltv.settings import with_defaults

from .conftest import DOMAIN

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()
NOW = "2026-10-13T06:00:00+00:00"
# About two interpreter frames per nesting level: 2,000 levels exceed the default recursion limit of 1,000, so
# re.compile raises RecursionError; the flow's 300-character cap makes this reachable only through stored data
DEEP_NESTING = "(" * 2000 + ")" * 2000


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


def _default(result: Any, name: str) -> Any:
    """Return the default of a form field (vol.Optional exposes it through key.default())."""
    for key in result["data_schema"].schema:
        if key == name:
            return key.default()
    msg = f"{name} not in form"
    raise AssertionError(msg)


def _suggestions(result: Any) -> dict[str, Any]:
    """Return every suggested value of a form, keyed by field name."""
    return {
        str(key): key.description["suggested_value"]
        for key in result["data_schema"].schema
        if key.description and "suggested_value" in key.description
    }


def _channel_options(result: Any) -> list[str]:
    for key, selector in result["data_schema"].schema.items():
        if key == "channels":
            return list(selector.config["options"])
    msg = "channels not in form"
    raise AssertionError(msg)


async def _edit(hass: HomeAssistant, entry: MockConfigEntry, subentry_id: str, basic: dict[str, Any]) -> Any:
    """Run the edit flow: basic form -> preview (or preview_empty) -> save."""
    result = await entry.start_subentry_reconfigure_flow(hass, subentry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], basic)
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] in {"preview", "preview_empty"}
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {"next_step_id": "save"})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    return result


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


@pytest.mark.parametrize(
    "pattern",
    [
        pytest.param("(", id="syntax-error"),
        pytest.param("a{99999999999}", id="repeat-overflow"),
        pytest.param(DEEP_NESTING, id="deep-nesting"),
    ],
)
async def test_corrupt_pattern_keeps_previous_matches(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
    caplog: pytest.LogCaptureFixture,
    pattern: str,
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(FEED, calendars=(("A", {"include": "tagesschau"}), ("B", {"channels": ["zdf.de"]})))
    a_id = _subentry_id(entry, "A")
    b_id = _subentry_id(entry, "B")
    a_events = await _summaries(hass, "calendar.a")
    assert a_events == ["Das Erste: Tagesschau"]

    # Hand-edited storage: A's pattern bypasses the flow's validation; B's edit fires the one listener call
    object.__setattr__(entry.subentries[a_id], "data", MappingProxyType({"include": pattern}))
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


PHASE1_DATA = {"channels": ["daserste.de"], "channel_regex": "", "include": "", "exclude": ""}


async def test_phase1_calendar_edit_keeps_events(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(FEED, calendars=(("A", PHASE1_DATA),))
    a_id = _subentry_id(entry, "A")
    before = await _summaries(hass, "calendar.a")
    assert before == ["Das Erste: Formel 1: Großer Preis von Mexiko", "Das Erste: Tagesschau"]

    # The pre-filled values, submitted unchanged
    await _edit(hass, entry, a_id, {"name": "A", **PHASE1_DATA})

    stored = dict(entry.subentries[a_id].data)
    assert stored == with_defaults(PHASE1_DATA)
    assert len(stored) == 14
    assert await _summaries(hass, "calendar.a") == before


async def test_missing_channel_stays_selectable(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(FEED, calendars=(("A", {"channels": ["gone.de", "zdf.de"]}),))
    a_id = _subentry_id(entry, "A")

    result = await entry.start_subentry_reconfigure_flow(hass, a_id)
    assert result["type"] is FlowResultType.FORM
    assert _channel_options(result) == ["daserste.de", "gone.de", "zdf.de"]
    assert _suggested(result, "channels") == ["gone.de", "zdf.de"]

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"name": "A", "channels": ["gone.de", "zdf.de"]}
    )
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "preview"


async def test_rename_via_edit_flow(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(FEED, calendars=(("A", {"include": "tagesschau"}),))
    a_id = _subentry_id(entry, "A")

    await _edit(hass, entry, a_id, {"name": "Renamed", "include": "tagesschau"})

    assert entry.subentries[a_id].title == "Renamed"
    device = dr.async_get(hass).async_get_device_by_identifier((DOMAIN, a_id), entry.entry_id)
    assert device is not None
    assert device.name == "Renamed"
    state = hass.states.get("calendar.a")
    assert state is not None
    assert state.attributes["friendly_name"] == "Renamed"
    assert hass.states.get("calendar.renamed") is None


async def test_edit_to_empty_filters_shows_all(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(FEED, calendars=(("A", {"include": "tagesschau"}),))
    a_id = _subentry_id(entry, "A")

    # Cleared optional fields arrive as missing keys
    await _edit(hass, entry, a_id, {"name": "A"})

    assert sorted(await _summaries(hass, "calendar.a")) == [
        "Das Erste: Formel 1: Großer Preis von Mexiko",
        "Das Erste: Tagesschau",
        "ZDF: heute",
        "ZDF: heute",
    ]


async def test_edit_on_unloaded_source_aborts(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED, calendars=(("A", {"include": "tagesschau"}),))
    a_id = _subentry_id(entry, "A")
    entry.mock_state(hass, ConfigEntryState.SETUP_RETRY)

    result = await entry.start_subentry_reconfigure_flow(hass, a_id)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "source_not_loaded"


async def test_back_in_edit_flow_keeps_edits(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(FEED, calendars=(("A", {"include": "tagesschau"}),))
    a_id = _subentry_id(entry, "A")

    result = await entry.start_subentry_reconfigure_flow(hass, a_id)
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {"name": "A", "include": "formel"})
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {"next_step_id": "back"})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "basic"
    assert _suggested(result, "include") == "formel"

    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {"name": "A", "include": "formel"})
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {"next_step_id": "save"})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.subentries[a_id].data["include"] == "formel"


SAT_DATA = {CONF_CHANNELS: ["daserste.de"], CONF_WEEKDAYS: ["sat"], CONF_TITLE_TEMPLATE: "{title}"}
SAT_CALENDARS = (("Sat", SAT_DATA), ("Plain", {CONF_CHANNELS: ["zdf.de"]}))


async def test_advanced_checkbox_prechecked_on_edit(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
    berlin_tz: None,
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(FEED, calendars=SAT_CALENDARS)
    sat_id = _subentry_id(entry, "Sat")
    plain_id = _subentry_id(entry, "Plain")
    calls = aioclient_mock.call_count
    runtime = entry.runtime_data
    epg = runtime.coordinator.data
    entity_plain = runtime.calendars[plain_id]
    assert await _summaries(hass, "calendar.sat") == []

    result = await entry.start_subentry_reconfigure_flow(hass, sat_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "basic"
    # D-03: stored advanced values pre-check the box
    assert _default(result, CONF_ADVANCED) is True

    # A calendar holding only defaults starts unchecked
    plain = await entry.start_subentry_reconfigure_flow(hass, plain_id)
    assert plain["type"] is FlowResultType.FORM
    assert _default(plain, CONF_ADVANCED) is False
    hass.config_entries.subentries.async_abort(plain["flow_id"])

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {CONF_NAME: "Sat", CONF_CHANNELS: ["daserste.de"], CONF_ADVANCED: True}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "advanced"
    suggestions = _suggestions(result)
    assert suggestions[CONF_WEEKDAYS] == ["sat"]
    assert suggestions[CONF_TITLE_TEMPLATE] == "{title}"

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {**suggestions, CONF_WEEKDAYS: ["tue"]}
    )
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "preview"
    assert result["description_placeholders"]["count"] == "2"

    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {"next_step_id": "save"})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()

    stored = dict(entry.subentries[sat_id].data)
    assert stored[CONF_WEEKDAYS] == ["tue"]
    assert stored[CONF_TITLE_TEMPLATE] == "{title}"
    assert CONF_ADVANCED not in stored
    assert await _summaries(hass, "calendar.sat") == ["Formel 1: Großer Preis von Mexiko", "Tagesschau"]
    # D-04, D-19: applied in place, no download, no parse, no reload, sibling untouched
    assert aioclient_mock.call_count == calls
    assert entry.runtime_data is runtime
    assert runtime.coordinator.data is epg
    assert runtime.calendars[plain_id] is entity_plain


async def test_unchecking_advanced_keeps_stored_values(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
    berlin_tz: None,
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(FEED, calendars=SAT_CALENDARS)
    sat_id = _subentry_id(entry, "Sat")

    result = await entry.start_subentry_reconfigure_flow(hass, sat_id)
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {CONF_NAME: "Sat", CONF_CHANNELS: ["daserste.de"], CONF_ADVANCED: False}
    )
    # Unchecked: no advanced step; the stored Saturday-only window still applies
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "preview_empty"

    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {"next_step_id": "save"})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()

    assert dict(entry.subentries[sat_id].data) == with_defaults(SAT_DATA)
    assert await _summaries(hass, "calendar.sat") == []
