"""Shared pytest configuration for the XMLTV Calendar integration tests."""

import builtins
import sys
import threading
from typing import TYPE_CHECKING, Any

import pytest
from homeassistant.config_entries import SOURCE_USER, ConfigSubentryData
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

# Must be imported before the hass fixture resolves `custom_components` to the phcc testing package
import custom_components.xmltv_calendar  # noqa: F401
from custom_components.xmltv_calendar.const import (
    CONF_NAIVE_TIMEZONE,
    CONF_OFFSET_MINUTES,
    CONF_REFRESH_HOURS,
    CONF_REFRESH_MODE,
    CONF_REFRESH_TIME,
    CONF_URL,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterable, Mapping

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

FEED_URL = "https://epg.example.com/guide.xml"

DOMAIN = "xmltv_calendar"

SECTION_TIMEZONE = "timezone"  # form-only section key of the url/file steps, never stored


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Allow Home Assistant to load integrations from custom_components in every test."""


@pytest.fixture(autouse=True)
def hass_config_dir(hass_tmp_config_dir: str) -> str:
    """Give every test its own config dir, so cache files never leak into phcc's shared testing_config."""
    return hass_tmp_config_dir


@pytest.fixture
def forbid_loop_io(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail when integration code calls open() on the event-loop thread (HA's detector is off in tests)."""
    loop_thread = threading.get_ident()
    real_open = builtins.open

    def guarded(*args: Any, **kwargs: Any) -> Any:
        caller = sys._getframe(1).f_code.co_filename
        if threading.get_ident() == loop_thread and "custom_components/xmltv_calendar" in caller:
            msg = f"blocking open() on the event loop from {caller}"
            raise AssertionError(msg)
        return real_open(*args, **kwargs)

    monkeypatch.setattr(builtins, "open", guarded)


@pytest.fixture
async def berlin_tz(hass: HomeAssistant) -> None:
    """Run the test in Europe/Berlin instead of the phcc default US/Pacific."""
    await hass.config.async_set_time_zone("Europe/Berlin")


@pytest.fixture
def setup_xmltv(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> Callable[..., Awaitable[MockConfigEntry]]:
    """Return an async factory that sets up a URL source entry with calendar subentries."""

    async def _setup(
        feed: bytes,
        calendars: Iterable[tuple[str, Mapping[str, Any]]] = (("Test", {}),),
        *,
        url: str = FEED_URL,
        options: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> MockConfigEntry:
        aioclient_mock.get(url, content=feed, headers=dict(headers) if headers is not None else None)
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="Test EPG",
            data={"source_type": "url", "url": url},
            options=dict(options) if options is not None else {"refresh_hours": 24},
            subentries_data=[
                ConfigSubentryData(subentry_type="calendar", title=title, data=dict(data), unique_id=None)
                for title, data in calendars
            ],
        )
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        return entry

    return _setup


def _settings_input(refresh_mode: str, naive_timezone: str, offset_minutes: float) -> dict[str, Any]:
    """Return the shared settings fields of the url and file steps (the section values arrive nested)."""
    return {
        CONF_REFRESH_MODE: refresh_mode,
        SECTION_TIMEZONE: {CONF_NAIVE_TIMEZONE: naive_timezone, CONF_OFFSET_MINUTES: offset_minutes},
    }


def _schedule_input(refresh_mode: str, refresh_hours: float, refresh_time: str | None) -> dict[str, Any]:
    """Return the schedule step input: a time for daily mode, else the interval in hours."""
    if refresh_mode == "daily":
        return {CONF_REFRESH_TIME: refresh_time}
    return {CONF_REFRESH_HOURS: refresh_hours}


async def add_url_source(
    hass: HomeAssistant,
    url: str = FEED_URL,
    *,
    refresh_mode: str = "interval",
    refresh_hours: float = 24,
    refresh_time: str | None = None,
    naive_timezone: str = "utc",
    offset_minutes: float = 0,
) -> Any:
    """
    Drive menu -> url -> download progress -> schedule; return the name-step result.

    Any earlier non-progress result (url form with errors, abort) is returned as is, so callers can assert on it.
    """
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "url"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_URL: url, **_settings_input(refresh_mode, naive_timezone, offset_minutes)}
    )
    if result["type"] is not FlowResultType.SHOW_PROGRESS:
        return result
    await hass.async_block_till_done()
    result = await hass.config_entries.flow.async_configure(result["flow_id"])
    if result["type"] is not FlowResultType.FORM or result["step_id"] != "schedule":
        return result
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], _schedule_input(refresh_mode, refresh_hours, refresh_time)
    )


async def complete_calendar_flow(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    basic: Mapping[str, Any],
    advanced: Mapping[str, Any] | None = None,
) -> Any:
    """Add a calendar through the subentry flow: basic form -> [advanced] -> preview (or preview_empty) -> save."""
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "calendar"), context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "basic"
    last_form = dict(basic)
    if advanced is not None:
        result = await hass.config_entries.subentries.async_configure(result["flow_id"], {**basic, "advanced": True})
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "advanced"
        last_form = dict(advanced)
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], last_form)
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] in {"preview", "preview_empty"}
    return await hass.config_entries.subentries.async_configure(result["flow_id"], {"next_step_id": "save"})
