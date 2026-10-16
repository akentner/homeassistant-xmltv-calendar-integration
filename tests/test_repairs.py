"""Repairs issue for a source that keeps failing (SRC-11, D-17, D-18)."""

import gzip
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiohttp
import pytest
from homeassistant.config_entries import ConfigEntryState, ConfigSubentryData
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.translation import async_get_translations
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.xmltv_calendar.const import CONF_REFRESH_MODE, CONF_REFRESH_TIME, REFRESH_MODE_DAILY

from .conftest import DOMAIN, FEED_URL

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()
NOW = "2026-10-13T06:00:00+00:00"  # 08:00 in Europe/Berlin
SECRET_URL = "https://epg.example.com/guide.xml?token=s3cret"  # noqa: S105 - fake token the issue must not show
OCTET_STREAM = {"content-type": "application/octet-stream"}
DAILY_18_15 = {CONF_REFRESH_MODE: REFRESH_MODE_DAILY, CONF_REFRESH_TIME: "18:15"}
pytestmark = [pytest.mark.freeze_time(NOW), pytest.mark.usefixtures("berlin_tz")]


def _serve(aioclient_mock: AiohttpClientMocker, url: str = FEED_URL, **kwargs: Any) -> None:
    """Forget earlier requests and responses, then answer `url` with `kwargs`."""
    aioclient_mock.clear_requests()
    aioclient_mock.get(url, **kwargs)


def _issue(hass: HomeAssistant, entry: MockConfigEntry) -> ir.IssueEntry | None:
    return ir.async_get(hass).async_get_issue(DOMAIN, f"source_failing_{entry.entry_id}")


@pytest.fixture
def feed_path(tmp_path: Path) -> Path:
    """Write the feed into a resolved temporary directory (is_allowed_path compares resolved paths)."""
    path = tmp_path.resolve() / "guide.xml"
    path.write_bytes(FEED)
    return path


async def _summaries(hass: HomeAssistant, entity_id: str) -> list[str]:
    response = await hass.services.async_call(
        "calendar",
        "get_events",
        {"entity_id": entity_id, "start_date_time": "2026-10-13T00:00:00+00:00", "duration": {"hours": 24}},
        blocking=True,
        return_response=True,
    )
    return [event["summary"] for event in response[entity_id]["events"]]


async def _setup_file_entry(hass: HomeAssistant, feed_path: Path) -> MockConfigEntry:
    """Set up a file source entry with one calendar, its directory on the allowlist."""
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
    return entry


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


async def test_failing_since_survives_restart(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: Any,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED)  # refresh_hours 24, cache written at NOW
    _serve(aioclient_mock, exc=aiohttp.ClientError())
    await _refresh_at(hass, freezer, entry, timedelta(hours=1))
    await _refresh_at(hass, freezer, entry, timedelta(hours=25, seconds=1))
    assert _issue(hass, entry) is not None

    # A restart: the entry unloads and Home Assistant does not restore non-persistent issues
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    ir.async_delete_issue(hass, DOMAIN, f"source_failing_{entry.entry_id}")
    freezer.move_to(NOW)
    freezer.tick(timedelta(hours=26))
    _serve(aioclient_mock, exc=aiohttp.ClientError())

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Set up from the stale cache, before its background refresh
    assert entry.state is ConfigEntryState.LOADED
    assert aioclient_mock.call_count == 0
    assert _issue(hass, entry) is not None

    coordinator = entry.runtime_data.coordinator
    failed_at = dt_util.utcnow() + timedelta(seconds=2)
    freezer.move_to(failed_at)
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert aioclient_mock.call_count == 1
    # Third consecutive failure: the backoff continues at 1 h instead of starting over at 5 min
    assert coordinator.health.consecutive_failures == 3
    assert coordinator.next_refresh_at == failed_at + timedelta(hours=1)


async def test_setup_retries_count_toward_the_issue(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: Any,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    # Registered before setup_xmltv's own mock, so the host is down from the start
    aioclient_mock.get(FEED_URL, exc=aiohttp.ClientError())
    entry = await setup_xmltv(FEED)
    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert _issue(hass, entry) is None

    freezer.move_to(NOW)
    freezer.tick(timedelta(hours=24, seconds=1))
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY
    issue = _issue(hass, entry)
    assert issue is not None
    assert issue.translation_placeholders == {"source": "Test EPG", "last_success": "-"}


async def test_daily_first_failure_after_24h_raises_no_issue(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: Any,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    freezer.move_to("2026-10-12T16:15:00+00:00")  # 18:15 Berlin
    entry = await setup_xmltv(FEED, options=DAILY_18_15)
    coordinator = entry.runtime_data.coordinator
    _serve(aioclient_mock, exc=aiohttp.ClientError())

    # The first failure comes 24 h after the last success: the streak starts here
    for at in ("2026-10-13T16:15:00+00:00", "2026-10-14T16:15:00+00:00"):
        freezer.move_to(at)
        await coordinator.async_refresh()
        assert coordinator.last_update_success is False
        assert _issue(hass, entry) is None

    freezer.move_to("2026-10-14T16:15:01+00:00")
    await coordinator.async_refresh()
    assert _issue(hass, entry) is not None


async def test_failures_keep_last_good_data(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: Any,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED, calendars=(("Formel 1", {"channels": ["daserste.de"]}),))
    coordinator = entry.runtime_data.coordinator
    previous = coordinator.data
    events = await _summaries(hass, "calendar.formel_1")
    _serve(aioclient_mock, exc=aiohttp.ClientError())

    await _refresh_at(hass, freezer, entry, timedelta(hours=1))

    assert coordinator.last_update_success is False
    assert coordinator.data is previous
    state = hass.states.get("calendar.formel_1")
    assert state is not None
    assert state.state == "off"
    assert await _summaries(hass, "calendar.formel_1") == events

    # Formel 1 airs 10:00-11:30 UTC; retries keep failing on the way there
    freezer.move_to("2026-10-13T10:00:00+00:00")
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert aioclient_mock.call_count >= 2
    assert coordinator.last_update_success is False
    assert coordinator.data is previous
    state = hass.states.get("calendar.formel_1")
    assert state.state == "on"
    assert state.attributes["message"] == "Das Erste: Formel 1: Großer Preis von Mexiko"


@pytest.mark.parametrize("source_type", ["url-304", "file-unchanged"])
async def test_not_modified_and_unchanged_file_count_as_success(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: Any,
    feed_path: Path,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    source_type: str,
) -> None:
    if source_type == "url-304":
        entry = await setup_xmltv(FEED, headers={"ETag": '"v1"'})
        _serve(aioclient_mock, exc=aiohttp.ClientError())
    else:
        entry = await _setup_file_entry(hass, feed_path)
        hass.config.allowlist_external_dirs = set()
    await _refresh_at(hass, freezer, entry, timedelta(hours=1))
    await _refresh_at(hass, freezer, entry, timedelta(hours=25, seconds=1))
    assert _issue(hass, entry) is not None

    if source_type == "url-304":
        _serve(aioclient_mock, status=304)
    else:
        hass.config.allowlist_external_dirs = {str(feed_path.parent)}
    await _refresh_at(hass, freezer, entry, timedelta(hours=26))

    coordinator = entry.runtime_data.coordinator
    assert coordinator.last_update_success is True
    assert coordinator.health.failing_since is None
    assert coordinator.health.consecutive_failures == 0
    assert _issue(hass, entry) is None


async def test_remove_entry_deletes_issue(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    aioclient_mock: AiohttpClientMocker,
    freezer: Any,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED)
    _serve(aioclient_mock, exc=aiohttp.ClientError())
    await _refresh_at(hass, freezer, entry, timedelta(hours=1))
    await _refresh_at(hass, freezer, entry, timedelta(hours=25, seconds=1))
    assert _issue(hass, entry) is not None

    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()

    assert _issue(hass, entry) is None
    assert f"{DOMAIN}.{entry.entry_id}" not in hass_storage
