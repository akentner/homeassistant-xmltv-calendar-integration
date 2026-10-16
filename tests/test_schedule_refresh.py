"""End-to-end refresh scheduling through Home Assistant: daily slot in the HA time zone, interval, re-arm (SRC-05)."""

from datetime import datetime
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigSubentry
from pytest_homeassistant_custom_component.common import async_fire_time_changed

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()
DAILY_18_15 = {"refresh_mode": "daily", "refresh_time": "18:15"}


async def _step_to(hass: HomeAssistant, freezer: Any, iso: str) -> None:
    freezer.move_to(iso)
    async_fire_time_changed(hass)
    # Scheduled refreshes run as background tasks (download, then parse in the executor)
    await hass.async_block_till_done(wait_background_tasks=True)


async def test_daily_slot_refreshes_at_local_time(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    berlin_tz: None,
    freezer: Any,
) -> None:
    freezer.move_to("2026-10-13T16:00:00+00:00")
    entry = await setup_xmltv(FEED, options=DAILY_18_15)
    assert aioclient_mock.call_count == 1

    # 18:15 Europe/Berlin (CEST) is 16:15 UTC
    await _step_to(hass, freezer, "2026-10-13T16:14:59+00:00")
    assert aioclient_mock.call_count == 1

    await _step_to(hass, freezer, "2026-10-13T16:15:01+00:00")
    assert aioclient_mock.call_count == 2
    assert entry.runtime_data.coordinator.next_refresh_at == datetime.fromisoformat("2026-10-14T16:15:00+00:00")

    await _step_to(hass, freezer, "2026-10-14T16:15:01+00:00")
    assert aioclient_mock.call_count == 3


async def test_interval_source_refreshes_every_interval(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
) -> None:
    freezer.move_to("2026-10-13T06:00:00+00:00")
    await setup_xmltv(FEED, options={"refresh_hours": 2})
    assert aioclient_mock.call_count == 1

    await _step_to(hass, freezer, "2026-10-13T07:59:00+00:00")
    assert aioclient_mock.call_count == 1

    await _step_to(hass, freezer, "2026-10-13T08:00:01+00:00")
    assert aioclient_mock.call_count == 2


async def test_rearm_after_calendar_readded(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    berlin_tz: None,
    freezer: Any,
) -> None:
    freezer.move_to("2026-10-13T16:00:00+00:00")
    entry = await setup_xmltv(FEED, options=DAILY_18_15)
    assert aioclient_mock.call_count == 1

    # Removing the only calendar drops the last listener and unschedules the refresh
    freezer.move_to("2026-10-13T16:05:00+00:00")
    (subentry_id,) = entry.subentries
    assert hass.config_entries.async_remove_subentry(entry, subentry_id)
    await hass.async_block_till_done()

    # The new calendar's listener re-arms the timer; a delay remembered from 16:00 would fire at 16:25
    freezer.move_to("2026-10-13T16:10:00+00:00")
    subentry = ConfigSubentry(data=MappingProxyType({}), subentry_type="calendar", title="New", unique_id=None)
    assert hass.config_entries.async_add_subentry(entry, subentry)
    await hass.async_block_till_done()
    assert hass.states.get("calendar.new") is not None

    await _step_to(hass, freezer, "2026-10-13T16:15:01+00:00")
    assert aioclient_mock.call_count == 2
