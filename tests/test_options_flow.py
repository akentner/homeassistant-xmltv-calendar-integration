"""Source options flow: schedule and timezone settings are editable after setup (CFG-02, D-04..D-07, D-16)."""

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.data_entry_flow import FlowResultType, InvalidData

from custom_components.xmltv_calendar.const import (
    CONF_NAIVE_TIMEZONE,
    CONF_OFFSET_MINUTES,
    CONF_REFRESH_HOURS,
    CONF_REFRESH_MODE,
    CONF_REFRESH_TIME,
)

from .conftest import FEED_URL, SECTION_TIMEZONE

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

NOW = "2026-10-13T06:00:00+00:00"  # 08:00 in Europe/Berlin
pytestmark = [pytest.mark.freeze_time(NOW), pytest.mark.usefixtures("berlin_tz")]

FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()

# One programme with offset-less times: 20:00 read as UTC is 22:00 in Berlin
NAIVE_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<tv>
  <channel id="daserste.de"><display-name>Das Erste</display-name></channel>
  <programme channel="daserste.de" start="20261013200000" stop="20261013201500"><title>Tagesschau</title></programme>
</tv>
"""

FULL_OPTIONS = {"refresh_mode": "interval", "refresh_hours": 24, "naive_timezone": "utc", "offset_minutes": 0}


def _schema_key(result: Any, name: str) -> Any:
    """Return the voluptuous marker for `name` in a form result."""
    for key in result["data_schema"].schema:
        if key == name:
            return key
    msg = f"{name} not in form"
    raise AssertionError(msg)


def _timezone_defaults(result: Any) -> dict[str, Any]:
    """Return the defaults of the collapsed timezone section of an init form."""
    timezone = result["data_schema"].schema[_schema_key(result, SECTION_TIMEZONE)]
    return {str(key): key.default() for key in timezone.schema.schema}


def _settings(refresh_mode: str, naive_timezone: str = "utc", offset_minutes: float = 0) -> dict[str, Any]:
    """Return an init step submission; the timezone values arrive nested in their section."""
    return {
        CONF_REFRESH_MODE: refresh_mode,
        SECTION_TIMEZONE: {CONF_NAIVE_TIMEZONE: naive_timezone, CONF_OFFSET_MINUTES: offset_minutes},
    }


@pytest.fixture
def reload_calls(hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Record every scheduled reload; the real reload still runs."""
    calls: list[str] = []
    original = hass.config_entries.async_schedule_reload

    def spy(entry_id: str) -> None:
        calls.append(entry_id)
        original(entry_id)

    monkeypatch.setattr(hass.config_entries, "async_schedule_reload", spy)
    return calls


async def test_options_flow_switch_to_daily(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    reload_calls: list[str],
) -> None:
    entry = await setup_xmltv(FEED)
    assert aioclient_mock.call_count == 1
    runtime = entry.runtime_data

    # 1. The init step offers the refresh mode and the timezone section, pre-filled from the stored options
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    assert _schema_key(result, CONF_REFRESH_MODE).default() == "interval"
    assert _timezone_defaults(result) == {CONF_NAIVE_TIMEZONE: "utc", CONF_OFFSET_MINUTES: 0}

    # 2. Daily mode asks only for the time
    result = await hass.config_entries.options.async_configure(result["flow_id"], _settings("daily"))
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "schedule"
    assert CONF_REFRESH_TIME in result["data_schema"].schema
    assert CONF_REFRESH_HOURS not in result["data_schema"].schema

    # 3. Saving stores the complete option contract; the TimeSelector's "HH:MM:SS" is stored as "HH:MM"
    result = await hass.config_entries.options.async_configure(result["flow_id"], {CONF_REFRESH_TIME: "18:15:00"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert dict(entry.options) == {
        "refresh_mode": "daily",
        "refresh_hours": 24,
        "refresh_time": "18:15",
        "naive_timezone": "utc",
        "offset_minutes": 0,
    }

    # 4. The diffing listener reloads the source once; the reload re-parses the fresh cache without a download
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data is not runtime
    assert reload_calls == [entry.entry_id]
    assert aioclient_mock.call_count == 1
    # The cache was fetched at 08:00 local, after yesterday's 18:15 slot: next refresh today at 18:15 local
    assert entry.runtime_data.coordinator.next_refresh_at == datetime.fromisoformat("2026-10-13T16:15:00+00:00")


async def _save_options(
    hass: HomeAssistant, entry: MockConfigEntry, settings: dict[str, Any], schedule: dict[str, Any]
) -> dict[str, Any]:
    """Drive init -> schedule with the given submissions and return the final result."""
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], settings)
    assert result["step_id"] == "schedule"
    return await hass.config_entries.options.async_configure(result["flow_id"], schedule)


async def _starts(hass: HomeAssistant) -> list[str]:
    response = await hass.services.async_call(
        "calendar",
        "get_events",
        {"entity_id": "calendar.test", "start_date_time": "2026-10-13T00:00:00+02:00", "duration": {"hours": 24}},
        blocking=True,
        return_response=True,
    )
    return [event["start"] for event in response["calendar.test"]["events"]]


async def test_options_prefill_for_pre_phase3_entry(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    reload_calls: list[str],
) -> None:
    # D-06: an entry stored before Phase 3 only holds refresh_hours; the missing keys mean the defaults
    entry = await setup_xmltv(FEED, options={"refresh_hours": 12})

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert _schema_key(result, CONF_REFRESH_MODE).default() == "interval"
    assert _timezone_defaults(result) == {CONF_NAIVE_TIMEZONE: "utc", CONF_OFFSET_MINUTES: 0}
    result = await hass.config_entries.options.async_configure(result["flow_id"], _settings("interval"))
    assert _schema_key(result, CONF_REFRESH_HOURS).default() == 12

    result = await hass.config_entries.options.async_configure(result["flow_id"], {CONF_REFRESH_HOURS: 12})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert dict(entry.options) == {**FULL_OPTIONS, "refresh_hours": 12}
    # The first save writes the full contract, so the source reloads once, from its cache
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert reload_calls == [entry.entry_id]
    assert aioclient_mock.call_count == 1


async def test_switching_back_prefills_previous_values(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(
        FEED, options={**FULL_OPTIONS, "refresh_mode": "daily", "refresh_hours": 6, "refresh_time": "18:15"}
    )

    # Daily -> interval offers the previously stored interval
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert _schema_key(result, CONF_REFRESH_MODE).default() == "daily"
    result = await hass.config_entries.options.async_configure(result["flow_id"], _settings("interval"))
    assert _schema_key(result, CONF_REFRESH_HOURS).default() == 6
    result = await hass.config_entries.options.async_configure(result["flow_id"], {CONF_REFRESH_HOURS: 6})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.runtime_data.coordinator.source_options.refresh_mode == "interval"

    # A later switch back to daily suggests the previously stored time (the inactive field is kept, not erased)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert _schema_key(result, CONF_REFRESH_MODE).default() == "interval"
    result = await hass.config_entries.options.async_configure(result["flow_id"], _settings("daily"))
    assert _schema_key(result, CONF_REFRESH_TIME).description == {"suggested_value": "18:15:00"}


async def test_options_timezone_change_shifts_events_without_download(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    await setup_xmltv(NAIVE_FEED)
    entry = hass.config_entries.async_entries("xmltv_calendar")[0]
    assert await _starts(hass) == ["2026-10-13T22:00:00+02:00"]

    result = await _save_options(hass, entry, _settings("interval", "local", 0), {CONF_REFRESH_HOURS: 24})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    # D-16: the reload re-parses the cached feed with the new interpretation; no download
    assert await _starts(hass) == ["2026-10-13T20:00:00+02:00"]
    assert aioclient_mock.call_count == 1


async def test_options_flow_has_no_url_or_path(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED)
    data = dict(entry.data)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert {str(key) for key in result["data_schema"].schema} == {CONF_REFRESH_MODE, SECTION_TIMEZONE}

    result = await hass.config_entries.options.async_configure(result["flow_id"], _settings("interval", "local", -60))
    result = await hass.config_entries.options.async_configure(result["flow_id"], {CONF_REFRESH_HOURS: 6})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    # D-04: only the options change; the source identity stays fixed
    assert dict(entry.data) == data == {"source_type": "url", "url": FEED_URL}
    assert dict(entry.options) == {**FULL_OPTIONS, "refresh_hours": 6, "naive_timezone": "local", "offset_minutes": -60}


async def test_identical_options_do_not_reload(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    reload_calls: list[str],
) -> None:
    entry = await setup_xmltv(FEED, options=FULL_OPTIONS)
    runtime = entry.runtime_data

    result = await _save_options(hass, entry, _settings("interval"), {CONF_REFRESH_HOURS: 24})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    assert dict(entry.options) == FULL_OPTIONS
    assert entry.runtime_data is runtime
    assert reload_calls == []
    assert aioclient_mock.call_count == 1


@pytest.mark.parametrize("hours", [0, 169])
async def test_options_bounds_are_enforced_for_hours(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    hours: int,
) -> None:
    entry = await setup_xmltv(FEED)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], _settings("interval"))
    with pytest.raises(InvalidData):
        await hass.config_entries.options.async_configure(result["flow_id"], {CONF_REFRESH_HOURS: hours})
    assert dict(entry.options) == {"refresh_hours": 24}


@pytest.mark.parametrize("offset", [-721, 721])
async def test_options_bounds_are_enforced_for_offset(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    offset: int,
) -> None:
    entry = await setup_xmltv(FEED)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    with pytest.raises(InvalidData):
        await hass.config_entries.options.async_configure(result["flow_id"], _settings("interval", "utc", offset))
    assert dict(entry.options) == {"refresh_hours": 24}
