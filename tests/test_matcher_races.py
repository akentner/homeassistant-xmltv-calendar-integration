"""Deterministic executor interleavings through the real subentry listener and coordinator."""

import asyncio
import threading
from contextlib import asynccontextmanager
from datetime import datetime
from typing import TYPE_CHECKING, Any
from unittest.mock import Mock

import pytest
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import async_capture_events

from .conftest import FEED_URL
from .test_new_match_event import (
    BASIC_FEED,
    EVENT,
    F1_ONLY,
    NOW,
    RACE_XML,
    SPRINT_XML,
    _programme_xml,
    _race,
    _refresh,
    _reload,
    _stored_seen,
    _with,
)
from .test_retention import RACE_MARKER, _retain_race, _retained_titles, _stored, _variant
from .test_sensor import SENSOR

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker


@asynccontextmanager
async def _held_filter(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[tuple[Callable[[], Awaitable[None]], Callable[[], None]]]:
    """Gate one real executor call; neither the HA loop nor teardown waits on a thread lock."""
    from custom_components.xmltv_calendar import matcher as module

    entered = threading.Event()
    entered_async = asyncio.Event()
    release = threading.Event()
    real = module._apply_filter

    def held(*args: Any) -> Any:
        if not entered.is_set():
            entered.set()
            hass.loop.call_soon_threadsafe(entered_async.set)
            assert release.wait(5), "executor gate was not released"
        return real(*args)

    async def wait_entered() -> None:
        await asyncio.wait_for(entered_async.wait(), 5)
        assert entered.is_set()

    monkeypatch.setattr(module, "_apply_filter", held)
    try:
        yield wait_entered, release.set
    finally:
        release.set()


async def _deliver(aioclient_mock: AiohttpClientMocker, entry: MockConfigEntry, feed: bytes) -> None:
    """Deliver distinct coordinator data without draining tasks until the executor gate is released."""
    aioclient_mock.clear_requests()
    aioclient_mock.get(FEED_URL, content=feed)
    await entry.runtime_data.coordinator.async_refresh()


@pytest.mark.parametrize("disabled", [False, True], ids=["enabled", "disabled"])
@pytest.mark.parametrize("narrow", [False, True], ids=["widen", "narrow"])
async def test_data_during_config_preserves_baseline_and_retention(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    monkeypatch: pytest.MonkeyPatch,
    aioclient_mock: AiohttpClientMocker,
    hass_storage: dict[str, Any],
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    disabled: bool,
    narrow: bool,
) -> None:
    from custom_components.xmltv_calendar.xmltv.render import event_uid

    freezer.move_to(NOW)
    entry = await setup_xmltv(BASIC_FEED, calendars=(("F1", {}),) if narrow else F1_ONLY)
    if disabled:
        er.async_get(hass).async_update_entity("calendar.f1", disabled_by=er.RegistryEntryDisabler.USER)
        await _reload(hass, entry)
        assert hass.states.get("calendar.f1") is None
    (sid,) = entry.subentries
    if narrow:
        # The dropped race is already stored; ended ZDF is still in the previous feed.
        freezer.move_to("2026-10-13T12:00:00+00:00")
        await _refresh(hass, aioclient_mock, entry, _variant(1, BASIC_FEED, RACE_MARKER))
        assert "Formel 1: Großer Preis von Mexiko" in _retained_titles(await _stored(hass_storage, entry))
        data = {"channels": ["daserste.de"], "include": "Tagesschau|Rennen|Sprint"}
        feed = _variant(2, _with(RACE_XML), RACE_MARKER)
    else:
        data = {"channels": ["daserste.de", "zdf.de"]}
        feed = _with(RACE_XML)
    events = async_capture_events(hass, EVENT)
    old_epg = entry.runtime_data.coordinator.data
    async with _held_filter(hass, monkeypatch) as (entered, release):
        assert hass.config_entries.async_update_subentry(entry, entry.subentries[sid], data=data)
        await entered()
        await _deliver(aioclient_mock, entry, feed)
        assert entry.runtime_data.coordinator.data is not old_epg
        release()
    await hass.async_block_till_done()

    uid = event_uid(_race())
    assert [event.data for event in events] == [
        {
            "entity_id": "calendar.f1",
            "calendar": "F1",
            "title": "Formel 1: Rennen",
            "summary": "Das Erste: Formel 1: Rennen",
            "channel": "Das Erste",
            "channel_id": "daserste.de",
            "start": "2026-10-14T16:00:00+02:00",
            "end": "2026-10-14T18:00:00+02:00",
            "uid": uid,
        }
    ]
    matcher = entry.runtime_data.matchers[sid]
    seen = await _stored_seen(hass_storage, entry)
    assert {event_uid(p) for p in matcher._feed_matches} <= seen.keys()
    assert uid in seen
    assert _retained_titles(await _stored(hass_storage, entry)) == []
    if narrow:
        assert [p.title for p in matcher._feed_matches] == ["Tagesschau", "Formel 1: Rennen"]
        assert hass.states.get(SENSOR).attributes["title"] == "Tagesschau"
    else:
        assert len([key for key in seen if key.startswith("zdf.de-")]) == 2
        assert hass.states.get(SENSOR).attributes["title"] == "Formel 1: Großer Preis von Mexiko"

    await _refresh(hass, aioclient_mock, entry, feed)
    await _reload(hass, entry)
    await _refresh(hass, aioclient_mock, entry, feed)
    assert len(events) == 1
    await _refresh(hass, aioclient_mock, entry, feed.replace(b"</tv>", SPRINT_XML + b"</tv>"))
    assert [event.data["title"] for event in events] == ["Formel 1: Rennen", "Formel 1: Sprint"]


async def _accept_edit(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch, entry: MockConfigEntry, data: dict[str, Any]
) -> None:
    """Wait for the actual listener to accept an edit, not for all held HA tasks to finish."""
    from custom_components.xmltv_calendar import matcher as module

    accepted = asyncio.Event()
    real = module._build_spec

    def build(*args: Any) -> Any:
        result = real(*args)
        accepted.set()
        return result

    with monkeypatch.context() as patch:
        patch.setattr(module, "_build_spec", build)
        (sid,) = entry.subentries
        assert hass.config_entries.async_update_subentry(entry, entry.subentries[sid], data=data)
        await asyncio.wait_for(accepted.wait(), 5)


@pytest.mark.parametrize("pattern", ["", "  \n", "("], ids=["valid", "normalized", "invalid"])
async def test_template_only_edit_does_not_scan(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    monkeypatch: pytest.MonkeyPatch,
    aioclient_mock: AiohttpClientMocker,
    hass_storage: dict[str, Any],
    caplog: pytest.LogCaptureFixture,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    pattern: str,
) -> None:
    from custom_components.xmltv_calendar import matcher as module

    entry = await _retain_race(hass, freezer, aioclient_mock, setup_xmltv)
    live = _programme_xml("daserste.de", "20261013133000 +0200", "20261013160000 +0200", "Live")
    await _refresh(hass, aioclient_mock, entry, _variant(2, _with(live), RACE_MARKER))
    (sid,) = entry.subentries
    runtime = entry.runtime_data
    entity = runtime.calendars[sid]
    start = datetime.fromisoformat("2026-10-12T00:00:00+00:00")
    end = datetime.fromisoformat("2026-10-16T00:00:00+00:00")
    before = await entity.async_get_events(hass, start, end)
    seen = await _stored_seen(hass_storage, entry)
    calls = aioclient_mock.call_count
    scan = Mock(wraps=module._apply_filter)
    monkeypatch.setattr(module, "_apply_filter", scan)
    events = async_capture_events(hass, EVENT)
    assert hass.config_entries.async_update_subentry(
        entry,
        entry.subentries[sid],
        data={
            "channels": ["daserste.de"],
            "include": pattern,
            "title_template": "New {title}",
            "description_template": "On {channel_id}",
        },
    )
    await hass.async_block_till_done()
    assert scan.call_count == 0
    after = await entity.async_get_events(hass, start, end)
    assert [e.uid for e in after] == [e.uid for e in before]
    assert [e.summary for e in after] == ["New " + e.summary.removeprefix("Das Erste: ") for e in before]
    assert {e.description for e in after} == {"On daserste.de"}
    assert entity.event.summary == "New Live"
    assert hass.states.get("calendar.f1").attributes["message"] == "New Live"
    assert hass.states.get(SENSOR).attributes["summary"] == "New Tagesschau"
    assert "New Formel 1: Großer Preis von Mexiko" in [e.summary for e in after]
    assert await _stored_seen(hass_storage, entry) == seen
    assert entry.runtime_data is runtime
    assert aioclient_mock.call_count == calls
    assert events == []
    assert not runtime.matchers[sid].differs_from(entry.subentries[sid])
    warnings = [r.message for r in caplog.records if "stored filter pattern is invalid" in r.message]
    assert len(warnings) == int(pattern == "(")
    # An unrelated listener call must not re-log or re-apply the same bad stored diff base.
    hass.config_entries.async_update_entry(entry, title="Source renamed")
    await hass.async_block_till_done()
    assert [r.message for r in caplog.records if "stored filter pattern is invalid" in r.message] == warnings
    assert scan.call_count == 0


async def test_template_edit_during_data_preserves_new_event(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    monkeypatch: pytest.MonkeyPatch,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(BASIC_FEED, calendars=F1_ONLY)
    events = async_capture_events(hass, EVENT)
    async with _held_filter(hass, monkeypatch) as (entered, release):
        await _deliver(aioclient_mock, entry, _with(RACE_XML))
        await entered()
        await _accept_edit(hass, monkeypatch, entry, {"channels": ["daserste.de"], "title_template": "New {title}"})
        release()
    await hass.async_block_till_done()
    assert [(e.data["title"], e.data["summary"]) for e in events] == [("Formel 1: Rennen", "New Formel 1: Rennen")]
    assert set(events[0].data) == {
        "entity_id",
        "calendar",
        "title",
        "summary",
        "channel",
        "channel_id",
        "start",
        "end",
        "uid",
    }
    await _refresh(hass, aioclient_mock, entry, _with(RACE_XML))
    assert len(events) == 1


@pytest.mark.parametrize("order", ["config-data", "data-config", "config-config-data", "config-data-config"])
async def test_newer_edit_keeps_pending_config_semantics(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    monkeypatch: pytest.MonkeyPatch,
    aioclient_mock: AiohttpClientMocker,
    hass_storage: dict[str, Any],
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    order: str,
) -> None:
    entry = await _retain_race(hass, freezer, aioclient_mock, setup_xmltv)
    (sid,) = entry.subentries
    matcher = entry.runtime_data.matchers[sid]
    latest = {
        "channels": ["daserste.de"],
        "include": "Tagesschau|Rennen|Sprint",
        "title_template": "Latest {title}",
        "retention_days": 7,
    }
    feed = _variant(2, _with(RACE_XML), RACE_MARKER)
    events = async_capture_events(hass, EVENT)
    async with _held_filter(hass, monkeypatch) as (entered, release):
        for index, step in enumerate(order.split("-")):
            if step == "data":
                await _deliver(aioclient_mock, entry, feed)
            else:
                data = (
                    {"title_template": "Old {title}", "retention_days": 0}
                    if index == 0 and order.count("config") == 2
                    else latest
                )
                await _accept_edit(hass, monkeypatch, entry, data)
            if index == 0:
                await entered()
        release()
    await hass.async_block_till_done()
    assert matcher._config_revision == matcher._committed_config_revision == order.count("config")
    assert not matcher._config_pending
    assert [p.title for p in matcher._feed_matches] == ["Tagesschau", "Formel 1: Rennen"]
    assert _retained_titles(await _stored(hass_storage, entry)) == []
    assert hass.states.get(SENSOR).attributes["summary"] == "Latest Tagesschau"
    expected = [] if order.endswith("config") else ["Formel 1: Rennen"]
    assert [e.data["title"] for e in events] == expected
    assert all(e.data["summary"] == "Latest Formel 1: Rennen" for e in events)
    await _refresh(hass, aioclient_mock, entry, feed.replace(b"</tv>", SPRINT_XML + b"</tv>"))
    assert [e.data["title"] for e in events] == [*expected, "Formel 1: Sprint"]
    # Once the narrowing committed, a later widening cannot resurrect the dropped raw retained race.
    assert hass.config_entries.async_update_subentry(entry, entry.subentries[sid], data={"retention_days": 7})
    await hass.async_block_till_done()
    assert "Formel 1: Großer Preis von Mexiko" not in _retained_titles(await _stored(hass_storage, entry))


@pytest.mark.parametrize("operation", ["remove", "unload"])
async def test_held_config_teardown_does_not_commit(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    monkeypatch: pytest.MonkeyPatch,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    operation: str,
) -> None:
    from homeassistant.helpers.dispatcher import async_dispatcher_connect

    from custom_components.xmltv_calendar.matcher import signal_matches

    freezer.move_to(NOW)
    entry = await setup_xmltv(BASIC_FEED, calendars=F1_ONLY)
    runtime = entry.runtime_data
    (sid,) = entry.subentries
    boundary = asyncio.Event()
    real_forget = runtime.match_store.forget

    def forget(key: str) -> None:
        real_forget(key)
        boundary.set()

    monkeypatch.setattr(runtime.match_store, "forget", forget)
    events = async_capture_events(hass, EVENT)
    signal = Mock()
    unsub = async_dispatcher_connect(hass, signal_matches(sid), signal)
    async with _held_filter(hass, monkeypatch) as (entered, release):
        await _accept_edit(hass, monkeypatch, entry, {"channels": ["zdf.de"]})
        await entered()
        if operation == "remove":
            assert hass.config_entries.async_remove_subentry(entry, sid)
            await asyncio.wait_for(boundary.wait(), 5)
        else:
            assert await hass.config_entries.async_unload(entry.entry_id)
        put = Mock(wraps=runtime.match_store.put)
        monkeypatch.setattr(runtime.match_store, "put", put)
        signal.reset_mock()
        release()
    await hass.async_block_till_done()
    unsub()
    assert put.call_count == signal.call_count == 0
    assert events == []
    if operation == "remove":
        assert sid not in runtime.matchers
    else:
        assert not runtime.active
        assert runtime.match_store._store._delay_handle is None


async def test_retention_only_edits_zero_and_seven(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    aioclient_mock: AiohttpClientMocker,
    hass_storage: dict[str, Any],
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await _retain_race(hass, freezer, aioclient_mock, setup_xmltv)
    (sid,) = entry.subentries
    runtime = entry.runtime_data
    calls = aioclient_mock.call_count
    events = async_capture_events(hass, EVENT)
    for days, retained in [(7, ["Formel 1: Großer Preis von Mexiko"]), (0, []), (7, [])]:
        assert hass.config_entries.async_update_subentry(
            entry, entry.subentries[sid], data={"channels": ["daserste.de"], "retention_days": days}
        )
        await hass.async_block_till_done()
        assert _retained_titles(await _stored(hass_storage, entry)) == retained
        assert runtime.matchers[sid]._retention_days == days
        assert not runtime.matchers[sid]._config_pending
    assert entry.runtime_data is runtime
    assert aioclient_mock.call_count == calls
    assert events == []


async def test_newer_data_supersedes_held_data(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    monkeypatch: pytest.MonkeyPatch,
    aioclient_mock: AiohttpClientMocker,
    hass_storage: dict[str, Any],
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(BASIC_FEED, calendars=F1_ONLY)
    events = async_capture_events(hass, EVENT)
    async with _held_filter(hass, monkeypatch) as (entered, release):
        await _deliver(aioclient_mock, entry, _with(RACE_XML))
        await entered()
        await _deliver(aioclient_mock, entry, _with(SPRINT_XML))
        release()
    await hass.async_block_till_done()
    assert [e.data["title"] for e in events] == ["Formel 1: Sprint"]
    assert not any(uid.startswith("daserste.de-20261014T140000Z-") for uid in await _stored_seen(hass_storage, entry))


async def test_invalid_initial_filter_retention_edit_finishes(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(BASIC_FEED, calendars=(("F1", {"include": "("}),))
    (sid,) = entry.subentries
    events = async_capture_events(hass, EVENT)
    assert hass.config_entries.async_update_subentry(
        entry, entry.subentries[sid], data={"include": "(", "retention_days": 7, "title_template": "New {title}"}
    )
    await hass.async_block_till_done()
    matcher = entry.runtime_data.matchers[sid]
    assert not matcher._config_pending
    assert matcher._config_revision == matcher._committed_config_revision == 1
    assert matcher.match_count == 0
    assert hass.states.get(SENSOR).state == "unknown"
    assert events == []
