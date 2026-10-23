"""Production-path regressions for matching independently of entity admission."""

import asyncio
import threading
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.const import EVENT_HOMEASSISTANT_FINAL_WRITE, EVENT_HOMEASSISTANT_STOP
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from pytest_homeassistant_custom_component.common import async_capture_events, async_fire_time_changed

from .conftest import complete_calendar_flow
from .test_new_match_event import EVENT, NOW, _refresh, _reload, _stored_seen
from .test_retention import RACE_MARKER, RACE_SUMMARY, _retained_titles, _stored, _summaries, _variant
from .test_sensor import BASIC_FEED, F1, RACE, SENSOR

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker


async def test_disabled_calendar_keeps_matching(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    aioclient_mock: AiohttpClientMocker,
    hass_storage: dict[str, Any],
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    freezer.move_to(NOW)
    events = async_capture_events(hass, EVENT)
    entry = await setup_xmltv(BASIC_FEED, calendars=F1)
    registry = er.async_get(hass)
    registry.async_update_entity("calendar.f1", disabled_by=er.RegistryEntryDisabler.USER)
    await _reload(hass, entry)

    assert hass.states.get("calendar.f1") is None
    assert hass.states.get(SENSOR).state == "2026-10-13T10:00:00+00:00"
    assert events == []

    await _refresh(hass, aioclient_mock, entry, BASIC_FEED.replace(b"</tv>", RACE))
    state = hass.states.get(SENSOR)
    assert state.state == "2026-10-13T07:00:00+00:00"
    assert state.attributes["summary"] == "Das Erste: Formel 1: Rennen"
    seen = await _stored_seen(hass_storage, entry)
    (uid,) = [key for key in seen if key.startswith("daserste.de-20261013T070000Z-")]
    assert seen[uid] == 1791882000
    assert [event.data for event in events] == [
        {
            "entity_id": "calendar.f1",
            "calendar": "F1",
            "title": "Formel 1: Rennen",
            "summary": "Das Erste: Formel 1: Rennen",
            "channel": "Das Erste",
            "channel_id": "daserste.de",
            "start": "2026-10-13T09:00:00+02:00",
            "end": "2026-10-13T11:00:00+02:00",
            "uid": uid,
        }
    ]


async def test_disabled_counts_without_calendar_objects(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    monkeypatch: pytest.MonkeyPatch,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    from custom_components.xmltv_calendar.diagnostics import async_get_config_entry_diagnostics
    from custom_components.xmltv_calendar.sensor import LastFetchSensor

    monkeypatch.setattr(LastFetchSensor, "_attr_entity_registry_enabled_default", True)
    freezer.move_to(NOW)
    entry = await setup_xmltv(BASIC_FEED, calendars=(*F1, ("ZDF", {"channels": ["zdf.de"]})))
    registry = er.async_get(hass)
    registry.async_update_entity("calendar.f1", disabled_by=er.RegistryEntryDisabler.USER)
    await _reload(hass, entry)
    # HA never admits this presentation; consumers must not need even a constructed calendar facade.
    sid = next(sid for sid, sub in entry.subentries.items() if sub.title == "F1")
    entry.runtime_data.calendars.pop(sid)
    await _refresh(hass, aioclient_mock, entry, BASIC_FEED.replace(b"</tv>", RACE))

    assert hass.states.get("sensor.f1_last_fetch").attributes["matches"] == 3
    assert hass.states.get("sensor.zdf_last_fetch").attributes["matches"] == 2
    assert (await async_get_config_entry_diagnostics(hass, entry))["calendars"] == [
        {"title": "F1", "matches": 3, "retained": 0},
        {"title": "ZDF", "matches": 2, "retained": 0},
    ]
    assert hass.states.get(SENSOR).state == "2026-10-13T07:00:00+00:00"
    calls = aioclient_mock.call_count
    freezer.move_to("2026-10-13T07:00:00+00:00")
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(SENSOR).state == "2026-10-13T10:00:00+00:00"
    assert aioclient_mock.call_count == calls


async def test_disabled_edits_and_retained_reenable(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    aioclient_mock: AiohttpClientMocker,
    hass_storage: dict[str, Any],
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    from custom_components.xmltv_calendar.diagnostics import async_get_config_entry_diagnostics

    freezer.move_to(NOW)
    entry = await setup_xmltv(_variant(0), calendars=F1)
    registry = er.async_get(hass)
    for entity_id in ("calendar.f1", SENSOR):
        registry.async_update_entity(entity_id, disabled_by=er.RegistryEntryDisabler.USER)
    await _reload(hass, entry)
    (sid,) = entry.subentries
    freezer.move_to("2026-10-13T12:00:00+00:00")
    await _refresh(hass, aioclient_mock, entry, _variant(1, BASIC_FEED, RACE_MARKER))
    assert _retained_titles(await _stored(hass_storage, entry)) == ["Formel 1: Großer Preis von Mexiko"]
    assert (await async_get_config_entry_diagnostics(hass, entry))["calendars"] == [
        {"title": "F1", "matches": 1, "retained": 1}
    ]
    calls = aioclient_mock.call_count
    assert hass.config_entries.async_update_subentry(
        entry,
        entry.subentries[sid],
        data={"channels": ["daserste.de"], "title_template": "{{ title }}", "retention_days": 3},
    )
    await hass.async_block_till_done()
    assert aioclient_mock.call_count == calls
    await _reload(hass, entry)
    assert _retained_titles(await _stored(hass_storage, entry)) == ["Formel 1: Großer Preis von Mexiko"]
    for entity_id in ("calendar.f1", SENSOR):
        registry.async_update_entity(entity_id, disabled_by=None)
    await _reload(hass, entry)
    summaries = await _summaries(hass)
    assert "Formel 1: Großer Preis von Mexiko" in summaries
    assert RACE_SUMMARY not in summaries

    # Filter edits and template edits still reach the sensor with the calendar disabled.
    registry.async_update_entity("calendar.f1", disabled_by=er.RegistryEntryDisabler.USER)
    await _reload(hass, entry)
    assert hass.config_entries.async_update_subentry(
        entry,
        entry.subentries[sid],
        data={"channels": ["zdf.de"], "title_template": "{{ title }}"},
    )
    await hass.async_block_till_done()
    assert hass.states.get(SENSOR).attributes["summary"] == "heute"
    assert "Formel 1: Großer Preis von Mexiko" not in _retained_titles(await _stored(hass_storage, entry))
    assert hass.config_entries.async_update_subentry(entry, entry.subentries[sid], data={"channels": ["absent"]})
    await hass.async_block_till_done()
    assert hass.states.get(SENSOR).state == "unknown"


@asynccontextmanager
async def _held_filter(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[tuple[Callable[[], Awaitable[None]], Callable[[], None]]]:
    """Hold exactly one executor job with explicit entry/release signals, always releasing on failure."""
    from custom_components.xmltv_calendar import matcher as module

    entered = asyncio.Event()
    release = threading.Event()
    real = module._apply_filter
    first = True

    def held(*args: Any) -> Any:
        nonlocal first
        if first:
            first = False
            hass.loop.call_soon_threadsafe(entered.set)
            assert release.wait(5), "test did not release the executor gate"
        return real(*args)

    async def wait_entered() -> None:
        await asyncio.wait_for(entered.wait(), 5)

    monkeypatch.setattr(module, "_apply_filter", held)
    try:
        yield wait_entered, release.set
    finally:
        release.set()


async def test_stop_captures_and_invalidates_worker(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    monkeypatch: pytest.MonkeyPatch,
    aioclient_mock: AiohttpClientMocker,
    hass_storage: dict[str, Any],
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    from custom_components.xmltv_calendar.matcher import signal_matches

    from .conftest import FEED_URL

    freezer.move_to(NOW)
    entry = await setup_xmltv(BASIC_FEED, calendars=F1)
    (sid,) = entry.subentries
    runtime = entry.runtime_data
    events = async_capture_events(hass, EVENT)
    signalled = Mock()
    unsub = async_dispatcher_connect(hass, signal_matches(sid), signalled)
    freezer.move_to("2026-10-13T12:00:00+00:00")
    async with _held_filter(hass, monkeypatch) as (entered, release):
        aioclient_mock.clear_requests()
        aioclient_mock.get(FEED_URL, content=_variant(1, BASIC_FEED, RACE_MARKER))
        await runtime.coordinator.async_refresh()
        await entered()
        stopped = asyncio.Event()
        hass.bus.async_listen(EVENT_HOMEASSISTANT_STOP, lambda _: stopped.set())
        hass.bus.async_fire(EVENT_HOMEASSISTANT_STOP)
        await asyncio.wait_for(stopped.wait(), 5)
        put = Mock(wraps=runtime.match_store.put)
        monkeypatch.setattr(runtime.match_store, "put", put)
        release()
    await hass.async_block_till_done()
    hass.bus.async_fire(EVENT_HOMEASSISTANT_FINAL_WRITE)
    await hass.async_block_till_done()
    unsub()
    assert put.call_count == 0
    assert signalled.call_count == 0
    assert events == []
    assert _retained_titles(await _stored(hass_storage, entry, flush=False)) == ["Formel 1: Großer Preis von Mexiko"]
    matcher = runtime.matchers[sid]
    assert not matcher._active
    assert matcher._unsub_coordinator is matcher._unsub_stop is None
    matcher.async_stop()


@pytest.mark.parametrize("operation", ["remove", "reload", "source_remove"])
async def test_blocked_worker_teardown(  # noqa: PLR0915 -- explicit teardown boundary assertions
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    monkeypatch: pytest.MonkeyPatch,
    aioclient_mock: AiohttpClientMocker,
    hass_storage: dict[str, Any],
    setup_xmltv: Callable[..., Awaitable[Any]],
    operation: str,
) -> None:
    from custom_components.xmltv_calendar.cache import cache_key
    from custom_components.xmltv_calendar.matcher import signal_matches

    from .conftest import FEED_URL

    freezer.move_to(NOW)
    entry = await setup_xmltv(BASIC_FEED, calendars=F1)
    runtime = entry.runtime_data
    (sid,) = entry.subentries
    key = f"xmltv_calendar.matches.{cache_key(entry)}"
    events = async_capture_events(hass, EVENT)
    signalled = Mock()
    unsub = async_dispatcher_connect(hass, signal_matches(sid), signalled)
    boundary = asyncio.Event()
    real_flush = runtime.match_store.async_flush
    real_forget = runtime.match_store.forget

    async def flushed() -> None:
        await real_flush()
        boundary.set()

    def forgotten(subentry_id: str) -> None:
        real_forget(subentry_id)
        boundary.set()

    monkeypatch.setattr(runtime.match_store, "async_flush", flushed)
    monkeypatch.setattr(runtime.match_store, "forget", forgotten)
    async with _held_filter(hass, monkeypatch) as (entered, release):
        aioclient_mock.clear_requests()
        aioclient_mock.get(FEED_URL, content=BASIC_FEED.replace(b"</tv>", RACE))
        await runtime.coordinator.async_refresh()
        await entered()
        if operation == "remove":
            assert hass.config_entries.async_remove_subentry(entry, sid)
            task = None
        elif operation == "reload":
            task = asyncio.create_task(hass.config_entries.async_reload(entry.entry_id))
        else:
            task = asyncio.create_task(hass.config_entries.async_remove(entry.entry_id))
        await asyncio.wait_for(boundary.wait(), 5)
        assert not runtime.matchers.get(sid) or not runtime.matchers[sid]._active
        put = Mock(wraps=runtime.match_store.put)
        monkeypatch.setattr(runtime.match_store, "put", put)
        signalled.reset_mock()
        release()
    if task is not None:
        assert await asyncio.wait_for(task, 5)
    await hass.async_block_till_done()
    unsub()
    assert put.call_count == 0
    assert events == []
    if operation != "reload":
        assert signalled.call_count == 0
    if operation == "source_remove":
        assert key not in hass_storage
    elif operation == "remove":
        await real_flush()
        assert sid not in hass_storage[key]["data"]["calendars"]
    else:
        assert entry.runtime_data is not runtime
        assert runtime.match_store._store._delay_handle is None
        seen = await _stored_seen(hass_storage, entry)
        assert any(uid.startswith("daserste.de-20261013T070000Z-") for uid in seen)


async def test_failed_unload_keeps_runtime_live(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    monkeypatch: pytest.MonkeyPatch,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    from custom_components.xmltv_calendar import async_unload_entry

    freezer.move_to(NOW)
    entry = await setup_xmltv(BASIC_FEED, calendars=F1)
    runtime = entry.runtime_data
    with monkeypatch.context() as patch:
        patch.setattr(hass.config_entries, "async_unload_platforms", AsyncMock(return_value=False))
        assert not await async_unload_entry(hass, entry)
    events = async_capture_events(hass, EVENT)
    await _refresh(hass, aioclient_mock, entry, BASIC_FEED.replace(b"</tv>", RACE))
    assert len(events) == 1
    assert hass.states.get(SENSOR).state == "2026-10-13T07:00:00+00:00"
    assert entry.runtime_data is runtime


async def test_removed_during_initial_filter_does_not_recreate_presentation(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    monkeypatch: pytest.MonkeyPatch,
    hass_storage: dict[str, Any],
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    from custom_components.xmltv_calendar.cache import cache_key

    freezer.move_to(NOW)
    entry = await setup_xmltv(BASIC_FEED, calendars=())
    runtime = entry.runtime_data
    forgotten = asyncio.Event()
    real_forget = runtime.match_store.forget

    def forget(sid: str) -> None:
        real_forget(sid)
        forgotten.set()

    monkeypatch.setattr(runtime.match_store, "forget", forget)
    async with _held_filter(hass, monkeypatch) as (entered, release):
        await complete_calendar_flow(hass, entry, {"name": "Late", "channels": ["zdf.de"]})
        await entered()
        (sid,) = entry.subentries
        assert hass.config_entries.async_remove_subentry(entry, sid)
        await asyncio.wait_for(forgotten.wait(), 5)
        release()
    await hass.async_block_till_done()
    await runtime.match_store.async_flush()
    assert sid not in runtime.matchers
    assert sid not in runtime.calendars
    assert sid not in runtime.sensors
    assert sid not in hass_storage[f"xmltv_calendar.matches.{cache_key(entry)}"]["data"]["calendars"]


async def test_late_add_rename_and_entity_toggle_keep_one_matcher(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(BASIC_FEED, calendars=())
    events = async_capture_events(hass, EVENT)
    await complete_calendar_flow(hass, entry, {"name": "F1", "channels": ["daserste.de"]})
    await hass.async_block_till_done()
    (sid,) = entry.subentries
    matcher = entry.runtime_data.matchers[sid]
    listeners = len(entry.runtime_data.coordinator._listeners)
    await matcher.async_start()
    assert len(entry.runtime_data.coordinator._listeners) == listeners
    registry = er.async_get(hass)
    old_device = registry.async_get("calendar.f1").device_id
    registry.async_update_entity(
        "calendar.f1", new_entity_id="calendar.my_racing", disabled_by=er.RegistryEntryDisabler.USER
    )
    await hass.async_block_till_done()
    assert hass.config_entries.async_update_subentry(entry, entry.subentries[sid], title="Renamed")
    await hass.async_block_till_done()
    assert entry.runtime_data.matchers[sid] is matcher
    assert registry.async_get("calendar.my_racing").device_id == old_device
    assert events == []
    await _refresh(hass, aioclient_mock, entry, BASIC_FEED.replace(b"</tv>", RACE))
    assert [(event.data["entity_id"], event.data["calendar"]) for event in events] == [
        ("calendar.my_racing", "Renamed")
    ]
    registry.async_update_entity("calendar.my_racing", disabled_by=None)
    await hass.async_block_till_done()
    assert entry.runtime_data.matchers[sid] is matcher
    for _ in range(2):
        previous = entry.runtime_data
        await _reload(hass, entry)
        assert not previous.matchers[sid]._active
        assert len(entry.runtime_data.coordinator._listeners) == listeners
    assert len(events) == 1
