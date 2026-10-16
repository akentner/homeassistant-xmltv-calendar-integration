"""Diagnostics of a source entry: structure, state and counts, never feed content or secrets (SRC-12, D-21)."""

import json
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiohttp
import pytest
from homeassistant.config_entries import ConfigEntryState, ConfigSubentryData
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import get_diagnostics_for_config_entry

from custom_components.xmltv_calendar.diagnostics import async_get_config_entry_diagnostics

from .conftest import DOMAIN, FEED_URL

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Mapping

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker
    from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()
NOW = "2026-10-13T06:00:00+00:00"
# Fake credentials, token and validator the diagnostics must never show
SECRET_URL = "https://user:hunter2@epg.example.com/guide.xml?token=s3cret"  # noqa: S105
FEED_ETAG = '"v1-secret-etag"'
# basic.xml plus one programme without a start time, which the parser skips as malformed (WR-08)
MALFORMED_FEED = FEED.replace(
    b"</tv>",
    b'<programme channel="zdf.de" stop="20261013210000 +0200"><title>No start</title></programme>\n</tv>',
)
pytestmark = pytest.mark.freeze_time(NOW)


async def test_diagnostics_end_to_end(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(
        FEED,
        calendars=(("B", {"channels": ["zdf.de"]}), ("A", {})),
        url=SECRET_URL,
        headers={"ETag": FEED_ETAG},
    )

    result = await get_diagnostics_for_config_entry(hass, hass_client, entry)

    assert result["source"] == {"source_type": "url", "url": "https://epg.example.com/**REDACTED**"}
    assert result["options"] == {
        "refresh_mode": "interval",
        "refresh_hours": 24,
        "naive_timezone": "utc",
        "offset_minutes": 0,
    }
    assert result["health"] == {
        "last_success": NOW,
        "failing_since": None,
        "last_failure": None,
        "consecutive_failures": 0,
    }
    assert result["cache"] == {"fetched_at": NOW, "size": len(FEED), "has_etag": True, "has_last_modified": False}
    assert result["stats"] == {
        "programmes": 4,
        "channels": 2,
        "skipped_malformed": 0,
        "duplicates": 0,
        "inferred_stops": 0,
        "dropped_past": 0,
    }
    assert result["calendars"] == [{"title": "A", "matches": 4}, {"title": "B", "matches": 2}]
    assert result["next_refresh"] == "2026-10-14T06:00:00+00:00"
    dumped = json.dumps(result)
    for secret in ("hunter2", "user:", "s3cret", "guide.xml", "v1-secret-etag", "Tagesschau"):
        assert secret not in dumped


@pytest.fixture
def feed_path(tmp_path: Path) -> Path:
    """Write the feed into a resolved temporary directory (is_allowed_path compares resolved paths)."""
    path = tmp_path.resolve() / "guide.xml"
    path.write_bytes(FEED)
    return path


async def test_file_source_diagnostics(hass: HomeAssistant, feed_path: Path) -> None:
    hass.config.allowlist_external_dirs = {str(feed_path.parent)}
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Local",
        data={"source_type": "file", "path": str(feed_path)},
        options={"refresh_hours": 24},
        subentries_data=[ConfigSubentryData(subentry_type="calendar", title="Test", data={}, unique_id=None)],
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["source"] == {"source_type": "file", "path": "**REDACTED**/guide.xml"}
    assert result["cache"] is None
    assert result["calendars"] == [{"title": "Test", "matches": 4}]
    assert str(feed_path.parent) not in json.dumps(result)


async def test_failing_source_diagnostics(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: Any,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED)
    coordinator = entry.runtime_data.coordinator
    aioclient_mock.clear_requests()
    aioclient_mock.get(FEED_URL, exc=aiohttp.ClientError())
    for hours in (1, 2):
        freezer.move_to(NOW)
        freezer.tick(timedelta(hours=hours))
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["health"] == {
        "last_success": NOW,
        "failing_since": "2026-10-13T07:00:00+00:00",
        "last_failure": {"time": "2026-10-13T08:00:00+00:00", "reason": "unable_to_fetch"},
        "consecutive_failures": 2,
    }
    # The last good data stays in memory and is still described (D-19)
    assert result["stats"]["programmes"] == 4
    assert result["calendars"] == [{"title": "Test", "matches": 4}]


async def test_diagnostics_for_not_loaded_entry(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    # Registered before setup_xmltv's own mock, so the host is down from the start and no cache exists
    aioclient_mock.get(FEED_URL, exc=aiohttp.ClientError())
    entry = await setup_xmltv(FEED, url=FEED_URL)
    assert entry.state is ConfigEntryState.SETUP_RETRY

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["loaded"] is False
    assert result["source"] == {"source_type": "url", "url": "https://epg.example.com/**REDACTED**"}
    assert result["options"] == {
        "refresh_mode": "interval",
        "refresh_hours": 24,
        "naive_timezone": "utc",
        "offset_minutes": 0,
    }
    assert result["health"] == {
        "last_success": None,
        "failing_since": NOW,
        "last_failure": {"time": NOW, "reason": "unable_to_fetch"},
        "consecutive_failures": 1,
    }
    assert result["cache"] is None
    assert result["stats"] is None
    assert result["calendars"] == []
    assert result["next_refresh"] is None


async def test_diagnostics_never_refresh(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED)
    coordinator = entry.runtime_data.coordinator
    calls = aioclient_mock.call_count
    data = coordinator.data

    result = await async_get_config_entry_diagnostics(hass, entry)
    await hass.async_block_till_done()

    assert result["loaded"] is True
    assert aioclient_mock.call_count == calls
    assert coordinator.data is data


async def test_skipped_malformed_is_reported(
    hass: HomeAssistant, setup_xmltv: Callable[..., Awaitable[MockConfigEntry]]
) -> None:
    entry = await setup_xmltv(MALFORMED_FEED)

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["stats"]["skipped_malformed"] == 1
    assert result["stats"]["programmes"] == 4
    assert "No start" not in json.dumps(result)


@pytest.mark.parametrize(
    ("stored", "shown"),
    [
        (
            {"refresh_mode": "daily", "refresh_time": "18:15", "naive_timezone": "local", "offset_minutes": -60},
            {"refresh_mode": "daily", "refresh_time": "18:15", "naive_timezone": "local", "offset_minutes": -60},
        ),
        (
            {"refresh_hours": 12},
            {"refresh_mode": "interval", "refresh_hours": 12, "naive_timezone": "utc", "offset_minutes": 0},
        ),
    ],
    ids=["daily_local_offset", "defaults_filled_in"],
)
async def test_daily_and_timezone_options_are_shown(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    stored: Mapping[str, Any],
    shown: Mapping[str, Any],
) -> None:
    entry = await setup_xmltv(FEED, options=stored)

    result = await async_get_config_entry_diagnostics(hass, entry)

    # refresh_hours stays in the daily options (the stored default), so compare the shown keys
    assert {key: result["options"][key] for key in shown} == shown
