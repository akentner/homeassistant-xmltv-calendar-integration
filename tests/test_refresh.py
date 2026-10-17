"""Later refreshes of a URL source: conditional requests, unchanged feeds and manual refreshes (SRC-07, AUT-04)."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock

import aiohttp
import pytest
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMockResponse
from yarl import URL

from custom_components.xmltv_calendar import coordinator as coordinator_module
from custom_components.xmltv_calendar.xmltv.filter import FilterSpec

from .conftest import FEED_URL

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()
CHANGED_FEED = FEED.replace(b"Tagesschau", b"Tagesthemen")
DOMAIN = "xmltv_calendar"
NOW = "2026-10-13T06:00:00+00:00"
LAST_MODIFIED = "Tue, 13 Oct 2026 04:00:00 GMT"
VALIDATORS = {"ETag": '"v1"', "Last-Modified": LAST_MODIFIED}
pytestmark = pytest.mark.freeze_time(NOW)


class ParseCounter:
    """Counts calls of the coordinator's feed parser while delegating to the real one."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Wrap the coordinator-module `parse` (looked up at call time by `_parser`)."""
        self.calls = 0
        real = coordinator_module.parse

        def counting(*args: Any, **kwargs: Any) -> Any:
            self.calls += 1
            return real(*args, **kwargs)

        monkeypatch.setattr(coordinator_module, "parse", counting)


def _serve(aioclient_mock: AiohttpClientMocker, **kwargs: Any) -> None:
    """Forget earlier requests and responses, then answer the feed URL with `kwargs`."""
    aioclient_mock.clear_requests()
    aioclient_mock.get(FEED_URL, **kwargs)


def _request_headers(aioclient_mock: AiohttpClientMocker, index: int = 0) -> dict[str, str]:
    return dict(aioclient_mock.mock_calls[index][3] or {})


async def _summaries(hass: HomeAssistant, entity_id: str = "calendar.test") -> list[str]:
    response = await hass.services.async_call(
        "calendar",
        "get_events",
        {"entity_id": entity_id, "start_date_time": "2026-10-13T00:00:00+00:00", "duration": {"hours": 24}},
        blocking=True,
        return_response=True,
    )
    return [event["summary"] for event in response[entity_id]["events"]]


def _payload_path(hass: HomeAssistant, entry: MockConfigEntry) -> Path:
    return Path(hass.config.cache_path(DOMAIN, f"{entry.entry_id}.feed"))


def _without_start_from_cache(monkeypatch: pytest.MonkeyPatch, entry: MockConfigEntry) -> None:
    """
    Drop the data in memory and skip the cache-first start, so the refresh asks the server with the stored validators.

    The stale-while-revalidate start (03-02) normally serves any valid cache without a request, which makes a 304
    without data in memory unreachable; the coordinator still handles it (RESEARCH Pitfall 3).
    """
    coordinator = entry.runtime_data.coordinator
    coordinator.data = None
    monkeypatch.setattr(coordinator, "_async_start_from_cache", AsyncMock(return_value=None))


def _sequence(*responses: dict[str, Any]) -> Any:
    """Return a mock side effect that answers successive requests with `responses`, repeating the last one."""
    remaining = list(responses)

    async def side_effect(method: str, url: URL, data: Any) -> AiohttpClientMockResponse:
        kwargs = remaining.pop(0) if len(remaining) > 1 else remaining[0]
        return AiohttpClientMockResponse(method, URL(FEED_URL), **kwargs)

    return side_effect


async def test_unchanged_feed_answers_304_without_reparse(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: Any,
    monkeypatch: pytest.MonkeyPatch,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED, headers=VALIDATORS)
    coordinator = entry.runtime_data.coordinator
    previous = coordinator.data
    parses = ParseCounter(monkeypatch)
    _serve(aioclient_mock, status=304, headers={"ETag": '"v1"'})

    freezer.tick(timedelta(hours=1))
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert aioclient_mock.call_count == 1
    headers = _request_headers(aioclient_mock)
    assert headers.get("If-None-Match") == '"v1"'
    assert headers.get("If-Modified-Since") == LAST_MODIFIED
    assert parses.calls == 0
    assert coordinator.data is previous
    assert coordinator.last_update_success is True
    assert coordinator.cache_meta is not None
    assert coordinator.cache_meta.fetched_at == datetime.fromisoformat(NOW) + timedelta(hours=1)


async def test_304_with_new_validator_replaces_stored(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: Any,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED, headers=VALIDATORS)
    coordinator = entry.runtime_data.coordinator
    _serve(aioclient_mock, status=304, headers={"ETag": '"v1b"'})

    freezer.tick(timedelta(hours=1))
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert coordinator.cache_meta is not None
    assert coordinator.cache_meta.etag == '"v1b"'
    assert coordinator.cache_meta.last_modified == LAST_MODIFIED
    _serve(aioclient_mock, status=304)
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert _request_headers(aioclient_mock).get("If-None-Match") == '"v1b"'


async def test_update_entity_refreshes_now_with_validators(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    monkeypatch: pytest.MonkeyPatch,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED, headers={"ETag": '"v1"'})
    assert await async_setup_component(hass, "homeassistant", {})
    parses = ParseCounter(monkeypatch)
    _serve(aioclient_mock, status=304)

    # The cache is fresh (fetched at NOW, refresh every 24 h), yet a manual refresh asks the server at once (D-12)
    await hass.services.async_call("homeassistant", "update_entity", {"entity_id": "calendar.test"}, blocking=True)
    await hass.async_block_till_done()

    assert aioclient_mock.call_count == 1
    assert _request_headers(aioclient_mock).get("If-None-Match") == '"v1"'
    assert parses.calls == 0
    assert entry.runtime_data.coordinator.last_update_success is True


async def test_update_entity_on_any_calendar_refreshes_the_source(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    await setup_xmltv(FEED, calendars=(("A", {}), ("B", {})), headers={"ETag": '"v1"'})
    assert await async_setup_component(hass, "homeassistant", {})
    before_a = await _summaries(hass, "calendar.a")
    before_b = await _summaries(hass, "calendar.b")
    assert len(before_a) == 4
    _serve(aioclient_mock, status=304)

    await hass.services.async_call("homeassistant", "update_entity", {"entity_id": "calendar.b"}, blocking=True)
    await hass.async_block_till_done()

    assert aioclient_mock.call_count == 1
    assert await _summaries(hass, "calendar.a") == before_a
    assert await _summaries(hass, "calendar.b") == before_b


async def test_changed_feed_replaces_data_and_cache(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: Any,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED, headers={"ETag": '"v1"'})
    coordinator = entry.runtime_data.coordinator
    previous = coordinator.data
    _serve(aioclient_mock, content=CHANGED_FEED, headers={"ETag": '"v2"'})

    freezer.tick(timedelta(hours=1))
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert _request_headers(aioclient_mock).get("If-None-Match") == '"v1"'
    assert coordinator.data is not previous
    assert "Das Erste: Tagesthemen" in await _summaries(hass)
    assert "Das Erste: Tagesschau" not in await _summaries(hass)
    assert _payload_path(hass, entry).read_bytes() == CHANGED_FEED
    assert coordinator.cache_meta is not None
    assert coordinator.cache_meta.etag == '"v2"'

    _serve(aioclient_mock, status=304)
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert _request_headers(aioclient_mock).get("If-None-Match") == '"v2"'


async def test_identical_body_is_not_reparsed(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: Any,
    monkeypatch: pytest.MonkeyPatch,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED)  # the server sends neither ETag nor Last-Modified
    coordinator = entry.runtime_data.coordinator
    previous = coordinator.data
    parses = ParseCounter(monkeypatch)
    _serve(aioclient_mock, content=FEED)

    freezer.tick(timedelta(hours=1))
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert aioclient_mock.call_count == 1
    assert parses.calls == 0
    assert coordinator.data is previous
    assert coordinator.last_update_success is True
    assert coordinator.cache_meta is not None
    assert coordinator.cache_meta.fetched_at == datetime.fromisoformat(NOW) + timedelta(hours=1)


async def test_304_without_data_parses_cache(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    monkeypatch: pytest.MonkeyPatch,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED, headers={"ETag": '"v1"'})
    coordinator = entry.runtime_data.coordinator
    _without_start_from_cache(monkeypatch, entry)
    parses = ParseCounter(monkeypatch)
    _serve(aioclient_mock, status=304)

    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert aioclient_mock.call_count == 1
    assert _request_headers(aioclient_mock).get("If-None-Match") == '"v1"'
    assert parses.calls == 1
    assert coordinator.last_update_success is True
    assert coordinator.data is not None
    assert len(coordinator.data.programmes) == 4


async def test_304_without_usable_cache_refetches_unconditionally(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    monkeypatch: pytest.MonkeyPatch,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED, headers={"ETag": '"v1"'})
    coordinator = entry.runtime_data.coordinator
    _without_start_from_cache(monkeypatch, entry)
    _payload_path(hass, entry).unlink()
    _serve(aioclient_mock, side_effect=_sequence({"status": 304}, {"response": FEED, "headers": {"ETag": '"v1"'}}))

    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert aioclient_mock.call_count == 2
    assert _request_headers(aioclient_mock, 0).get("If-None-Match") == '"v1"'
    assert "If-None-Match" not in _request_headers(aioclient_mock, 1)
    assert coordinator.last_update_success is True
    assert coordinator.data is not None
    assert len(coordinator.data.programmes) == 4
    assert _payload_path(hass, entry).read_bytes() == FEED


async def test_unchanged_data_does_not_refilter(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: Any,
    monkeypatch: pytest.MonkeyPatch,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED, headers={"ETag": '"v1"'})
    coordinator = entry.runtime_data.coordinator
    before = await _summaries(hass)
    applies = 0
    real_apply = FilterSpec.apply

    def counting_apply(self: FilterSpec, *args: Any, **kwargs: Any) -> Any:
        nonlocal applies
        applies += 1
        return real_apply(self, *args, **kwargs)

    monkeypatch.setattr(FilterSpec, "apply", counting_apply)

    _serve(aioclient_mock, status=304)
    freezer.tick(timedelta(hours=1))
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert coordinator.last_update_success is True
    assert applies == 0

    _serve(aioclient_mock, exc=aiohttp.ClientError())
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert coordinator.last_update_success is False
    assert applies == 0
    assert hass.states.get("calendar.test").state != STATE_UNAVAILABLE
    assert await _summaries(hass) == before


@pytest.mark.parametrize("response", [{"status": 304}, {"content": FEED}])
async def test_expired_unchanged_feed_fails_without_reparse(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: Any,
    monkeypatch: pytest.MonkeyPatch,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    response: dict[str, Any],
) -> None:
    entry = await setup_xmltv(FEED, headers=VALIDATORS)
    coordinator = entry.runtime_data.coordinator
    previous = coordinator.data
    meta = coordinator.cache_meta
    parses = ParseCounter(monkeypatch)
    _serve(aioclient_mock, **response)
    freezer.move_to("2026-10-15T06:00:00+00:00")

    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert coordinator.last_update_success is False
    assert coordinator.last_exception.translation_key == "empty_feed"
    assert coordinator.health.consecutive_failures == 1
    assert coordinator.data is previous
    assert coordinator.cache_meta == meta
    assert parses.calls == 0
    assert aioclient_mock.call_count == 1
