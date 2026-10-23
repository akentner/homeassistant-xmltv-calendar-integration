"""Deterministic executor interleavings through the real subentry listener and coordinator."""

import asyncio
import threading
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

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
    _race,
    _refresh,
    _reload,
    _stored_seen,
    _with,
)
from .test_retention import RACE_MARKER, _retained_titles, _stored, _variant
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
