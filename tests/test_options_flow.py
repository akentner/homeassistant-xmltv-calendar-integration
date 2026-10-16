"""Source options flow: schedule and timezone settings are editable after setup (CFG-02, D-04..D-07, D-16)."""

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.data_entry_flow import FlowResultType

from custom_components.xmltv_calendar.const import (
    CONF_NAIVE_TIMEZONE,
    CONF_OFFSET_MINUTES,
    CONF_REFRESH_HOURS,
    CONF_REFRESH_MODE,
    CONF_REFRESH_TIME,
)

from .conftest import SECTION_TIMEZONE

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

NOW = "2026-10-13T06:00:00+00:00"  # 08:00 in Europe/Berlin
pytestmark = [pytest.mark.freeze_time(NOW), pytest.mark.usefixtures("berlin_tz")]

FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()


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
