"""Repairs issue for a source that keeps failing (SRC-11, D-17, D-18)."""

import gzip
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiohttp
import pytest
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.translation import async_get_translations

from .conftest import DOMAIN, FEED_URL

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()
NOW = "2026-10-13T06:00:00+00:00"  # 08:00 in Europe/Berlin
SECRET_URL = "https://epg.example.com/guide.xml?token=s3cret"  # noqa: S105 - fake token the issue must not show
OCTET_STREAM = {"content-type": "application/octet-stream"}
pytestmark = [pytest.mark.freeze_time(NOW), pytest.mark.usefixtures("berlin_tz")]


def _serve(aioclient_mock: AiohttpClientMocker, url: str = FEED_URL, **kwargs: Any) -> None:
    """Forget earlier requests and responses, then answer `url` with `kwargs`."""
    aioclient_mock.clear_requests()
    aioclient_mock.get(url, **kwargs)


def _issue(hass: HomeAssistant, entry: MockConfigEntry) -> ir.IssueEntry | None:
    return ir.async_get(hass).async_get_issue(DOMAIN, f"source_failing_{entry.entry_id}")


async def _refresh_at(hass: HomeAssistant, freezer: Any, entry: MockConfigEntry, delay: timedelta) -> None:
    """Move the clock to NOW + `delay` and refresh the source once."""
    freezer.move_to(NOW)
    freezer.tick(delay)
    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()


async def test_persistent_failure_raises_and_clears_issue(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: Any,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED)
    coordinator = entry.runtime_data.coordinator
    _serve(aioclient_mock, exc=aiohttp.ClientError())

    await _refresh_at(hass, freezer, entry, timedelta(hours=1))
    assert coordinator.last_update_success is False
    assert _issue(hass, entry) is None

    # Exactly 24 h after the first failure of the streak is not yet "more than 24 h"
    await _refresh_at(hass, freezer, entry, timedelta(hours=25))
    assert _issue(hass, entry) is None

    await _refresh_at(hass, freezer, entry, timedelta(hours=25, seconds=1))
    issue = _issue(hass, entry)
    assert issue is not None
    assert issue.translation_key == "source_failing_unable_to_fetch"
    assert issue.is_fixable is False
    assert issue.severity is ir.IssueSeverity.WARNING
    assert issue.translation_placeholders == {"source": "Test EPG", "last_success": "2026-10-13 08:00"}

    _serve(aioclient_mock, content=FEED)
    await _refresh_at(hass, freezer, entry, timedelta(hours=26))
    assert coordinator.last_update_success is True
    assert _issue(hass, entry) is None


async def test_issue_follows_the_latest_reason(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: Any,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    payload = gzip.compress(FEED)
    entry = await setup_xmltv(payload)
    _serve(aioclient_mock, exc=aiohttp.ClientError())
    await _refresh_at(hass, freezer, entry, timedelta(hours=1))

    _serve(aioclient_mock, content=payload[: len(payload) // 2], headers=OCTET_STREAM)
    await _refresh_at(hass, freezer, entry, timedelta(hours=25, seconds=1))

    issue = _issue(hass, entry)
    assert issue is not None
    assert issue.translation_key == "source_failing_invalid_feed"


async def test_issue_text_has_no_url(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: Any,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED, url=SECRET_URL)
    _serve(aioclient_mock, url=SECRET_URL, exc=aiohttp.ClientError())
    await _refresh_at(hass, freezer, entry, timedelta(hours=1))
    await _refresh_at(hass, freezer, entry, timedelta(hours=25, seconds=1))

    issue = _issue(hass, entry)
    assert issue is not None
    placeholders = issue.translation_placeholders or {}
    rendered = [str(value) for value in placeholders.values()]
    for language in ("en", "de"):
        texts = await async_get_translations(hass, language, "issues", [DOMAIN])
        prefix = f"component.{DOMAIN}.issues.{issue.translation_key}"
        title = texts[f"{prefix}.title"]
        description = texts[f"{prefix}.description"]
        rendered += [title.format(**placeholders), description.format(**placeholders)]
    for text in rendered:
        assert "s3cret" not in text
        assert "guide.xml" not in text
    assert "Test EPG" in rendered[-1]
