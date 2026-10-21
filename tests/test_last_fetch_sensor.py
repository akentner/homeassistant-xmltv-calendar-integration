"""Last-fetch diagnostic sensor: the source's last refresh run on every calendar device (AUT-06, D-20..D-24)."""

from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiohttp
import pytest
from homeassistant.config_entries import ConfigEntryState, ConfigSubentryData
from homeassistant.const import STATE_UNAVAILABLE, EntityCategory
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from .conftest import DOMAIN, FEED_URL

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from datetime import datetime

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()
CHANGED_FEED = FEED.replace(b"Tagesschau", b"Tagesthemen")
NOW = "2026-10-13T06:00:00+00:00"
LATER = "2026-10-13T07:00:00+00:00"
SENSOR = "sensor.test_last_fetch"
pytestmark = pytest.mark.freeze_time(NOW)


@pytest.fixture
def last_fetch_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enable the disabled-by-default sensor; phcc has no entity_registry_enabled_by_default fixture (Pitfall 7)."""
    from custom_components.xmltv_calendar.sensor import LastFetchSensor

    monkeypatch.setattr(LastFetchSensor, "_attr_entity_registry_enabled_default", True)


@pytest.mark.usefixtures("last_fetch_enabled")
async def test_download_shows_last_fetch(
    hass: HomeAssistant, setup_xmltv: Callable[..., Awaitable[MockConfigEntry]]
) -> None:
    await setup_xmltv(FEED, calendars=(("Test", {}),))

    state = hass.states.get(SENSOR)
    assert state is not None
    assert state.state == NOW
    attributes = state.attributes
    expected = {
        "trigger": "startup",
        "outcome": "downloaded",
        "http_status": 200,
        "failure_reason": None,
        "cache": "written",
        "sent_etag": False,
        "sent_last_modified": False,
        "bytes": len(FEED),
        "programmes": 4,
        "channels": 2,
        "matches": 4,
        "consecutive_failures": 0,
    }
    assert {key: attributes.get(key, "missing") for key in expected} == expected
    assert isinstance(attributes["parse_duration"], float)
    assert attributes["parse_duration"] >= 0
    assert isinstance(attributes["last_success"], str)
    assert isinstance(attributes["next_refresh"], str)


async def test_last_fetch_is_diagnostic_and_disabled_by_default(
    hass: HomeAssistant, setup_xmltv: Callable[..., Awaitable[MockConfigEntry]]
) -> None:
    entry = await setup_xmltv(FEED, calendars=(("Test", {}),))
    (subentry_id,) = entry.subentries

    registry = er.async_get(hass)
    sensor = registry.async_get(SENSOR)
    calendar = registry.async_get("calendar.test")
    assert sensor is not None
    assert calendar is not None
    assert sensor.entity_category is EntityCategory.DIAGNOSTIC
    assert sensor.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert sensor.unique_id == f"{subentry_id}_last_fetch"
    assert sensor.device_id == calendar.device_id
    assert hass.states.get(SENSOR) is None


def _serve(aioclient_mock: AiohttpClientMocker, **kwargs: Any) -> None:
    """Forget earlier requests and responses, then answer the feed URL with `kwargs`."""
    aioclient_mock.clear_requests()
    aioclient_mock.get(FEED_URL, **kwargs)


def _attributes(hass: HomeAssistant) -> dict[str, Any]:
    state = hass.states.get(SENSOR)
    assert state is not None
    return dict(state.attributes)


def _pick(attributes: dict[str, Any], *keys: str) -> dict[str, Any]:
    return {key: attributes.get(key, "missing") for key in keys}


async def _step_to(hass: HomeAssistant, freezer: Any, when: datetime) -> None:
    freezer.move_to(when)
    async_fire_time_changed(hass)
    # Scheduled refreshes run as background tasks (download, then parse in the executor)
    await hass.async_block_till_done(wait_background_tasks=True)


@pytest.mark.usefixtures("last_fetch_enabled")
async def test_not_modified_run(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: Any,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED, headers={"ETag": '"v1"'})
    assert await async_setup_component(hass, "homeassistant", {})
    coordinator = entry.runtime_data.coordinator
    listener_calls: list[None] = []
    unsubscribe = coordinator.async_add_listener(lambda: listener_calls.append(None))
    _serve(aioclient_mock, status=304)
    freezer.move_to(LATER)

    await hass.services.async_call("homeassistant", "update_entity", {"entity_id": "calendar.test"}, blocking=True)
    await hass.async_block_till_done()
    unsubscribe()

    # The data object did not change, so no coordinator listener ran, yet the sensor shows the run
    assert listener_calls == []
    assert hass.states.get(SENSOR).state == LATER
    assert _pick(
        _attributes(hass),
        "trigger",
        "outcome",
        "http_status",
        "cache",
        "sent_etag",
        "bytes",
        "parse_duration",
        "programmes",
    ) == {
        "trigger": "manual",
        "outcome": "not_modified",
        "http_status": 304,
        "cache": "touched",
        "sent_etag": True,
        "bytes": None,
        "parse_duration": None,
        "programmes": 4,
    }


@pytest.mark.usefixtures("last_fetch_enabled")
async def test_identical_body_run(
    hass: HomeAssistant,
    freezer: Any,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED)
    freezer.move_to(LATER)

    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get(SENSOR).state == LATER
    assert _pick(_attributes(hass), "trigger", "outcome", "http_status", "cache", "sent_etag", "bytes") == {
        "trigger": "manual",
        "outcome": "unchanged",
        "http_status": 200,
        "cache": "touched",
        "sent_etag": False,
        "bytes": len(FEED),
    }


@pytest.mark.usefixtures("last_fetch_enabled")
async def test_scheduled_run(
    hass: HomeAssistant,
    freezer: Any,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED)
    target = entry.runtime_data.coordinator.next_refresh_at

    await _step_to(hass, freezer, target + timedelta(seconds=1))

    assert hass.states.get(SENSOR).state == (target + timedelta(seconds=1)).isoformat()
    assert _attributes(hass)["trigger"] == "scheduled"


@pytest.mark.usefixtures("last_fetch_enabled")
async def test_failed_run_and_retry(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: Any,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED)
    coordinator = entry.runtime_data.coordinator
    _serve(aioclient_mock, status=500)
    freezer.move_to(LATER)

    await coordinator.async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get(SENSOR)
    assert state.state == LATER
    assert state.state != STATE_UNAVAILABLE
    assert _pick(
        _attributes(hass), "trigger", "outcome", "http_status", "failure_reason", "consecutive_failures", "programmes"
    ) == {
        "trigger": "manual",
        "outcome": "failed",
        "http_status": 500,
        "failure_reason": "unable_to_fetch",
        "consecutive_failures": 1,
        "programmes": 4,
    }

    # The backoff timer serves a retry
    await _step_to(hass, freezer, coordinator.next_refresh_at + timedelta(seconds=1))
    assert _pick(_attributes(hass), "trigger", "outcome", "consecutive_failures") == {
        "trigger": "retry",
        "outcome": "failed",
        "consecutive_failures": 2,
    }

    # A network error has no HTTP status
    _serve(aioclient_mock, exc=aiohttp.ClientError())
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert _pick(_attributes(hass), "outcome", "http_status") == {"outcome": "failed", "http_status": None}


@pytest.mark.usefixtures("last_fetch_enabled")
async def test_cache_start_and_revalidate(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: Any,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED)  # refresh_hours 24, cache written at NOW
    assert await hass.config_entries.async_unload(entry.entry_id)
    freezer.move_to("2026-10-14T07:00:00+00:00")  # NOW + 25 h: the cache is stale
    _serve(aioclient_mock, content=CHANGED_FEED)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert aioclient_mock.call_count == 0
    assert hass.states.get(SENSOR).state == "2026-10-14T07:00:00+00:00"
    attributes = _attributes(hass)
    assert _pick(attributes, "trigger", "outcome", "cache", "http_status", "programmes") == {
        "trigger": "startup",
        "outcome": "cache_start",
        "cache": "stale_hit",
        "http_status": None,
        "programmes": 4,
    }
    assert isinstance(attributes["parse_duration"], float)

    # The stale cache is refreshed about a second later
    await _step_to(hass, freezer, entry.runtime_data.coordinator.next_refresh_at + timedelta(seconds=1))
    assert aioclient_mock.call_count == 1
    assert _pick(_attributes(hass), "trigger", "outcome") == {"trigger": "revalidate", "outcome": "downloaded"}

    # Now fresh: a reload starts from the cache without a request
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert aioclient_mock.call_count == 1
    assert _pick(_attributes(hass), "trigger", "outcome", "cache") == {
        "trigger": "startup",
        "outcome": "cache_start",
        "cache": "fresh_hit",
    }


@pytest.fixture
def feed_path(tmp_path: Path) -> Path:
    """Write the feed into a resolved temporary directory (is_allowed_path compares resolved paths)."""
    path = tmp_path.resolve() / "guide.xml"
    path.write_bytes(FEED)
    return path


@pytest.mark.usefixtures("last_fetch_enabled")
async def test_file_source_runs(hass: HomeAssistant, feed_path: Path) -> None:
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

    attributes = _attributes(hass)
    assert _pick(attributes, "trigger", "outcome", "http_status", "cache", "bytes", "programmes") == {
        "trigger": "startup",
        "outcome": "read",
        "http_status": None,
        "cache": "none",
        "bytes": len(FEED),
        "programmes": 4,
    }
    assert isinstance(attributes["parse_duration"], float)

    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    assert _pick(_attributes(hass), "trigger", "outcome", "http_status") == {
        "trigger": "manual",
        "outcome": "unchanged",
        "http_status": None,
    }


@pytest.mark.usefixtures("last_fetch_enabled")
async def test_same_instant_runs_keep_the_latest(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    hass_storage: dict[str, Any],
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED)
    coordinator = entry.runtime_data.coordinator
    _serve(aioclient_mock, content=CHANGED_FEED)

    # Two manual refreshes at the same frozen instant: a download, then the same body again
    await coordinator.async_refresh()
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    stored = hass_storage[f"{DOMAIN}.{entry.entry_id}"]["data"]["attempt"]
    assert isinstance(stored, dict)
    assert _pick(stored, "time", "outcome") == {"time": NOW, "outcome": "unchanged"}
    assert hass.states.get(SENSOR).state == NOW
    assert _attributes(hass)["outcome"] == "unchanged"
