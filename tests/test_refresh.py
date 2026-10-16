"""Later refreshes of a URL source: conditional requests, unchanged feeds and manual refreshes (SRC-07, AUT-04)."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from custom_components.xmltv_calendar import coordinator as coordinator_module

from .conftest import FEED_URL

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()
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

    assert aioclient_mock.call_count == 1
    headers = _request_headers(aioclient_mock)
    assert headers.get("If-None-Match") == '"v1"'
    assert headers.get("If-Modified-Since") == LAST_MODIFIED
    assert parses.calls == 0
    assert coordinator.data is previous
    assert coordinator.last_update_success is True
    assert coordinator.cache_meta is not None
    assert coordinator.cache_meta.fetched_at == datetime.fromisoformat(NOW) + timedelta(hours=1)
