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

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterable, Mapping

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

FEED_URL = "https://epg.example.com/guide.xml"

DOMAIN = "xmltv_calendar"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Allow Home Assistant to load integrations from custom_components in every test."""


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
    ) -> MockConfigEntry:
        aioclient_mock.get(url, content=feed)
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="Test EPG",
            data={"source_type": "url", "url": url},
            options={"refresh_hours": 24},
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
