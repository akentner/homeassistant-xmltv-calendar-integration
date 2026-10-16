"""End-to-end refresh scheduling through Home Assistant: daily slot in the HA time zone, interval, re-arm (SRC-05)."""

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

import aiohttp
from homeassistant.config_entries import ConfigSubentry
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.xmltv_calendar import coordinator as coordinator_module
from custom_components.xmltv_calendar.const import (
    CONF_REFRESH_HOURS,
    CONF_REFRESH_MODE,
    CONF_REFRESH_TIME,
    REFRESH_MODE_DAILY,
)

from .conftest import FEED_URL

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    import pytest
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()
DAILY_18_15 = {CONF_REFRESH_MODE: REFRESH_MODE_DAILY, CONF_REFRESH_TIME: "18:15"}


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


async def test_daily_slot_served_once_when_timer_fires_early(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    berlin_tz: None,
    freezer: Any,
) -> None:
    freezer.move_to("2026-10-13T16:00:00+00:00")
    entry = await setup_xmltv(FEED, options=DAILY_18_15)
    coordinator = entry.runtime_data.coordinator
    assert aioclient_mock.call_count == 1
    assert coordinator.next_refresh_at == datetime.fromisoformat("2026-10-13T16:15:00+00:00")

    # HA arms its timer at int(loop.time()) + 0.05..0.5 s + interval, so it can fire up to ~0.95 s before the slot;
    # the coordinator cannot tell that refresh from this direct call. The host answers with the same body.
    freezer.move_to("2026-10-13T16:14:59.400000+00:00")
    await coordinator.async_refresh()
    assert aioclient_mock.call_count == 2
    assert coordinator.last_update_success is True
    assert coordinator.next_refresh_at == datetime.fromisoformat("2026-10-14T16:15:00+00:00")

    # The slot was served: no second request one second later
    await _step_to(hass, freezer, "2026-10-13T16:15:01+00:00")
    assert aioclient_mock.call_count == 2

    await _step_to(hass, freezer, "2026-10-14T16:15:01+00:00")
    assert aioclient_mock.call_count == 3
    assert coordinator.next_refresh_at == datetime.fromisoformat("2026-10-15T16:15:00+00:00")


async def test_daily_fast_failure_before_slot_backs_off_five_minutes(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    berlin_tz: None,
    freezer: Any,
) -> None:
    freezer.move_to("2026-10-13T16:00:00+00:00")
    entry = await setup_xmltv(FEED, options=DAILY_18_15)
    coordinator = entry.runtime_data.coordinator
    aioclient_mock.clear_requests()
    aioclient_mock.get(FEED_URL, exc=aiohttp.ClientError())

    # An early-fired timer whose request fails at once: the first backoff step, not a retry 0.6 s later
    failed_at = datetime.fromisoformat("2026-10-13T16:14:59.400000+00:00")
    freezer.move_to(failed_at)
    await coordinator.async_refresh()
    assert aioclient_mock.call_count == 1
    assert coordinator.last_update_success is False
    assert coordinator.health.consecutive_failures == 1
    assert coordinator.next_refresh_at == failed_at + timedelta(minutes=5)

    await _step_to(hass, freezer, "2026-10-13T16:15:01+00:00")
    assert aioclient_mock.call_count == 1
    assert coordinator.health.consecutive_failures == 1

    retry_at = coordinator.next_refresh_at + timedelta(seconds=1)
    await _step_to(hass, freezer, retry_at.isoformat())
    assert aioclient_mock.call_count == 2
    assert coordinator.health.consecutive_failures == 2
    assert coordinator.next_refresh_at == retry_at + timedelta(minutes=15)


async def test_manual_refresh_before_slot_keeps_the_slot(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    berlin_tz: None,
    freezer: Any,
) -> None:
    freezer.move_to("2026-10-13T16:00:00+00:00")
    entry = await setup_xmltv(FEED, options=DAILY_18_15)
    coordinator = entry.runtime_data.coordinator

    # A manual refresh minutes before the slot does not consume it (D-12)
    freezer.move_to("2026-10-13T16:10:00+00:00")
    await coordinator.async_refresh()
    assert aioclient_mock.call_count == 2
    assert coordinator.next_refresh_at == datetime.fromisoformat("2026-10-13T16:15:00+00:00")

    await _step_to(hass, freezer, "2026-10-13T16:15:01+00:00")
    assert aioclient_mock.call_count == 3
    assert coordinator.next_refresh_at == datetime.fromisoformat("2026-10-14T16:15:00+00:00")


async def test_manual_refresh_restarts_the_interval(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
) -> None:
    freezer.move_to("2026-10-13T06:00:00+00:00")
    entry = await setup_xmltv(FEED, options={CONF_REFRESH_HOURS: 2})
    coordinator = entry.runtime_data.coordinator

    # now + interval; a plain max(now, target) base would push it to 10:00
    freezer.move_to("2026-10-13T07:00:00+00:00")
    await coordinator.async_refresh()
    assert coordinator.next_refresh_at == datetime.fromisoformat("2026-10-13T09:00:00+00:00")


async def test_interval_source_refreshes_every_interval(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
) -> None:
    freezer.move_to("2026-10-13T06:00:00+00:00")
    await setup_xmltv(FEED, options={CONF_REFRESH_HOURS: 2})
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


async def test_failure_backoff_steps(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
) -> None:
    freezer.move_to("2026-10-13T06:00:00+00:00")
    entry = await setup_xmltv(FEED)  # refresh_hours 24
    coordinator = entry.runtime_data.coordinator
    aioclient_mock.clear_requests()
    aioclient_mock.get(FEED_URL, exc=aiohttp.ClientError())

    failed_at = datetime.fromisoformat("2026-10-13T07:00:00+00:00")
    freezer.move_to(failed_at)
    await coordinator.async_refresh()
    assert coordinator.next_refresh_at == failed_at + timedelta(minutes=5)

    # Each retry fires at its target and fails again: 15 min, 1 h, 3 h, 6 h, then 6 h again (D-10)
    for calls, step in enumerate(
        (timedelta(minutes=15), timedelta(hours=1), timedelta(hours=3), timedelta(hours=6), timedelta(hours=6)),
        start=2,
    ):
        failed_at = coordinator.next_refresh_at + timedelta(seconds=1)
        await _step_to(hass, freezer, failed_at.isoformat())
        assert aioclient_mock.call_count == calls
        assert coordinator.last_update_success is False
        assert coordinator.next_refresh_at == failed_at + step

    aioclient_mock.clear_requests()
    aioclient_mock.get(FEED_URL, content=FEED)
    succeeded_at = coordinator.next_refresh_at + timedelta(seconds=1)
    await _step_to(hass, freezer, succeeded_at.isoformat())
    assert aioclient_mock.call_count == 1
    assert coordinator.last_update_success is True
    assert coordinator.next_refresh_at == succeeded_at + timedelta(hours=24)


async def test_backoff_capped_by_interval(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
) -> None:
    freezer.move_to("2026-10-13T06:00:00+00:00")
    entry = await setup_xmltv(FEED, options={CONF_REFRESH_HOURS: 2})
    coordinator = entry.runtime_data.coordinator
    aioclient_mock.clear_requests()
    aioclient_mock.get(FEED_URL, exc=aiohttp.ClientError())

    for _ in range(4):
        freezer.tick(timedelta(minutes=1))
        await coordinator.async_refresh()

    # The 4th step (3 h) would pass the regular 2 h interval
    assert coordinator.next_refresh_at == dt_util.utcnow() + timedelta(hours=2)


async def test_backoff_capped_by_next_daily_slot(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    berlin_tz: None,
    freezer: Any,
) -> None:
    freezer.move_to("2026-10-13T15:00:00+00:00")
    entry = await setup_xmltv(FEED, options=DAILY_18_15)
    coordinator = entry.runtime_data.coordinator
    aioclient_mock.clear_requests()
    aioclient_mock.get(FEED_URL, exc=aiohttp.ClientError())

    freezer.move_to("2026-10-13T16:00:00+00:00")
    await coordinator.async_refresh()
    assert coordinator.next_refresh_at == datetime.fromisoformat("2026-10-13T16:05:00+00:00")

    # 15 min after 16:05Z would pass the 18:15 Berlin slot (16:15Z)
    freezer.move_to("2026-10-13T16:05:00+00:00")
    await coordinator.async_refresh()
    assert coordinator.next_refresh_at == datetime.fromisoformat("2026-10-13T16:15:00+00:00")


def _raise_runtime_error(*_args: Any, **_kwargs: Any) -> Any:
    msg = "boom"
    raise RuntimeError(msg)


async def test_unexpected_exception_backs_off_and_is_recorded(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    freezer.move_to("2026-10-13T06:00:00+00:00")
    entry = await setup_xmltv(FEED)
    coordinator = entry.runtime_data.coordinator
    previous = coordinator.data
    # A changed body, so the refresh parses instead of taking the identical-body shortcut
    aioclient_mock.clear_requests()
    aioclient_mock.get(FEED_URL, content=FEED + b"\n")
    # A latent parser bug (or MemoryError): neither FeedError nor UpdateFailed
    monkeypatch.setattr(coordinator_module, "parse", _raise_runtime_error)
    caplog.clear()

    failed_at = coordinator.next_refresh_at + timedelta(seconds=1)
    await _step_to(hass, freezer, failed_at.isoformat())
    assert aioclient_mock.call_count == 1
    health = coordinator.health
    assert health.consecutive_failures == 1
    assert health.failing_since == failed_at
    assert health.last_failure_reason == "unable_to_fetch"
    assert coordinator.next_refresh_at == failed_at + timedelta(minutes=5)
    assert isinstance(coordinator.last_exception, UpdateFailed)
    assert coordinator.last_exception.translation_key == "unable_to_fetch"
    # The last good data stays and the calendars stay available (SRC-08, D-19)
    assert coordinator.data is previous
    state = hass.states.get("calendar.test")
    assert state is not None
    assert state.state != "unavailable"
    # One content-free WARNING: the exception class, never its text (T-03-28)
    warnings = [
        record
        for record in caplog.records
        if record.name == "custom_components.xmltv_calendar.coordinator" and record.levelno == logging.WARNING
    ]
    assert len(warnings) == 1
    assert "RuntimeError" in warnings[0].getMessage()
    assert "boom" not in warnings[0].getMessage()
    assert warnings[0].exc_info is None

    # No once-per-second retry loop
    await _step_to(hass, freezer, (failed_at + timedelta(seconds=10)).isoformat())
    assert aioclient_mock.call_count == 1

    retry_at = coordinator.next_refresh_at + timedelta(seconds=1)
    await _step_to(hass, freezer, retry_at.isoformat())
    assert aioclient_mock.call_count == 2
    assert coordinator.health.consecutive_failures == 2
    assert coordinator.next_refresh_at == retry_at + timedelta(minutes=15)


async def test_cancelled_refresh_records_no_failure(
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    freezer.move_to("2026-10-13T06:00:00+00:00")
    entry = await setup_xmltv(FEED)
    coordinator = entry.runtime_data.coordinator
    target = coordinator.next_refresh_at

    async def _cancelled(*_args: Any, **_kwargs: Any) -> Any:
        raise asyncio.CancelledError

    monkeypatch.setattr(coordinator_module, "async_fetch_url", _cancelled)
    freezer.tick(timedelta(hours=1))
    # Home Assistant swallows a CancelledError when the refreshing task itself is not being cancelled
    await coordinator.async_refresh()

    health = coordinator.health
    assert health.consecutive_failures == 0
    assert health.failing_since is None
    assert health.last_failure_at is None
    assert coordinator.next_refresh_at == target
    assert isinstance(coordinator.last_exception, asyncio.CancelledError)
