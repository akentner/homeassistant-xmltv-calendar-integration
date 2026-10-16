"""Disk cache of a URL source: restarts and reloads use it while fresh (SRC-06, D-08, D-09)."""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiohttp
import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.xmltv_calendar import cache as cache_module
from custom_components.xmltv_calendar.cache import cache_key
from custom_components.xmltv_calendar.const import CONF_REFRESH_MODE, CONF_REFRESH_TIME, REFRESH_MODE_DAILY

from .conftest import FEED_URL

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()
NOW = "2026-10-13T06:00:00+00:00"
DOMAIN = "xmltv_calendar"
SECRET_URL = "https://epg.example.com/guide.xml?token=s3cret"  # noqa: S105 - fake token the Store must not hold
# Every programme ended more than a day before NOW, so the parser's keep_after drops them all
OUTDATED_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<tv>
  <channel id="zdf.de"><display-name>ZDF</display-name></channel>
  <programme channel="zdf.de" start="20261011100000 +0000" stop="20261011110000 +0000"><title>Old</title></programme>
</tv>
"""
CHANGED_FEED = FEED.replace(b"Tagesschau", b"Tagesthemen")
DAILY_18_15 = {CONF_REFRESH_MODE: REFRESH_MODE_DAILY, CONF_REFRESH_TIME: "18:15"}
pytestmark = pytest.mark.freeze_time(NOW)


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


def _stored_meta(hass_storage: dict[str, Any], entry: MockConfigEntry) -> Any:
    return hass_storage[f"{DOMAIN}.{entry.entry_id}"]["data"]["meta"]


def _serve(aioclient_mock: AiohttpClientMocker, url: str = FEED_URL, **kwargs: Any) -> None:
    aioclient_mock.clear_requests()
    aioclient_mock.get(url, **kwargs)


async def _step_to(hass: HomeAssistant, freezer: Any, iso: str) -> None:
    freezer.move_to(iso)
    async_fire_time_changed(hass)
    # Scheduled refreshes run as background tasks (download, then parse in the executor)
    await hass.async_block_till_done(wait_background_tasks=True)


async def _restart(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Unload and set the entry up again with the same storage and config dir, as an HA restart does."""
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_restart_uses_fresh_cache(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED)
    assert aioclient_mock.call_count == 1
    before = await _summaries(hass)
    assert len(before) == 4

    await _restart(hass, entry)

    assert entry.state is ConfigEntryState.LOADED
    assert aioclient_mock.call_count == 1
    assert await _summaries(hass) == before
    assert _payload_path(hass, entry).read_bytes() == FEED


async def test_reload_uses_fresh_cache(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED)
    before = await _summaries(hass)

    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert aioclient_mock.call_count == 1
    assert await _summaries(hass) == before
    assert _payload_path(hass, entry).read_bytes() == FEED


async def test_size_mismatch_redownloads(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED)
    path = _payload_path(hass, entry)
    # What a crash between the payload write and the metadata save can leave behind
    path.write_bytes(FEED[:-1])

    await _restart(hass, entry)

    assert entry.state is ConfigEntryState.LOADED
    assert aioclient_mock.call_count == 2
    assert path.stat().st_size == len(FEED)
    assert len(await _summaries(hass)) == 4


async def test_missing_payload_redownloads(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED)
    _payload_path(hass, entry).unlink()

    await _restart(hass, entry)

    assert entry.state is ConfigEntryState.LOADED
    assert aioclient_mock.call_count == 2
    assert len(await _summaries(hass)) == 4


async def test_corrupt_cached_payload_is_dropped(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    hass_storage: dict[str, Any],
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED)
    path = _payload_path(hass, entry)
    path.write_bytes(b"x" * len(FEED))  # right size, does not parse

    # Restart while the source is down: the bad payload must be gone, not kept for the next start
    _serve(aioclient_mock, exc=aiohttp.ClientError())
    await _restart(hass, entry)

    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert aioclient_mock.call_count == 1
    assert not path.exists()
    assert _stored_meta(hass_storage, entry) is None

    _serve(aioclient_mock, content=FEED)
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert aioclient_mock.call_count == 1
    assert "If-None-Match" not in (aioclient_mock.mock_calls[-1][3] or {})
    assert len(await _summaries(hass)) == 4
    assert path.read_bytes() == FEED


async def test_changed_source_ignores_cache(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED)
    other_url = "https://epg.example.com/other.xml"
    aioclient_mock.get(other_url, content=FEED.replace(b"Tagesschau", b"Tagesthemen"))
    assert await hass.config_entries.async_unload(entry.entry_id)
    hass.config_entries.async_update_entry(entry, data={"source_type": "url", "url": other_url})

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert aioclient_mock.call_count == 2
    assert aioclient_mock.mock_calls[-1][1].human_repr() == other_url
    assert "Das Erste: Tagesthemen" in await _summaries(hass)


async def test_empty_parse_is_not_cached(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(OUTDATED_FEED)

    assert not _payload_path(hass, entry).exists()
    # The Store may hold the source health (03-04), never payload metadata
    stored = hass_storage.get(f"{DOMAIN}.{entry.entry_id}")
    assert stored is None or stored["data"]["meta"] is None


async def test_cache_write_failure_is_tolerated(
    hass: HomeAssistant,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    def failing_write(*_args: Any, **_kwargs: Any) -> None:
        raise OSError

    monkeypatch.setattr(cache_module, "write_utf8_file", failing_write)
    caplog.set_level(logging.DEBUG, logger="custom_components.xmltv_calendar")

    entry = await setup_xmltv(FEED, url=SECRET_URL)

    assert entry.state is ConfigEntryState.LOADED
    assert len(await _summaries(hass)) == 4
    messages = [record.getMessage() for record in caplog.records if record.name.endswith(".cache")]
    assert any(entry.entry_id in message for message in messages)
    assert "s3cret" not in caplog.text
    assert "guide.xml" not in caplog.text


async def test_payload_is_private(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED)

    assert os.stat(_payload_path(hass, entry)).st_mode & 0o777 == 0o600  # noqa: PTH116


async def test_store_holds_no_url(
    hass_storage: dict[str, Any],
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED, url=SECRET_URL)

    dumped = json.dumps(hass_storage[f"{DOMAIN}.{entry.entry_id}"])
    assert _stored_meta(hass_storage, entry)["size"] == len(FEED)
    assert "s3cret" not in dumped
    assert "guide.xml" not in dumped


@pytest.mark.parametrize(("header", "field"), [("ETag", "etag"), ("Last-Modified", "last_modified")])
@pytest.mark.parametrize(
    ("value", "stored"),
    [
        ('"v1"', '"v1"'),
        ('W/"a1"', 'W/"a1"'),
        ("Tue, 13 Oct 2026 05:00:00 GMT", "Tue, 13 Oct 2026 05:00:00 GMT"),
        ("a" * 1024, "a" * 1024),
        ('"v1"\r\nX-Injected: 1', None),
        ("a" * 1025, None),
        ('"\u00fc"', None),
    ],
    ids=["quoted", "weak", "http-date", "1024-chars", "crlf", "1025-chars", "non-ascii"],
)
async def test_validators_are_cleaned(
    hass_storage: dict[str, Any],
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    header: str,
    field: str,
    value: str,
    stored: str | None,
) -> None:
    entry = await setup_xmltv(FEED, headers={header: value})

    assert _stored_meta(hass_storage, entry)[field] == stored


@pytest.mark.parametrize(
    ("unique_id", "expected"),
    [
        ("a" * 64, "a" * 64),
        (None, "entry01"),
        ("../evil", "2d6afc710923ce47ddbfb2dc8b851f633a91e032a2bfe3ec551e0ef4d1f4ed95"),
    ],
    ids=["hex-unique-id", "entry-id", "path-traversal"],
)
def test_cache_key_is_filesystem_safe(unique_id: str | None, expected: str) -> None:
    entry = MockConfigEntry(domain=DOMAIN, entry_id="entry01", unique_id=unique_id)

    assert cache_key(entry) == expected


async def test_remove_entry_deletes_cache(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED)
    path = _payload_path(hass, entry)
    assert path.exists()

    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()

    assert not path.exists()
    assert f"{DOMAIN}.{entry.entry_id}" not in hass_storage


async def test_stale_cache_shown_then_refreshed(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: Any,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED)  # refresh_hours 24, cache written at NOW
    cached = await _summaries(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)
    freezer.move_to("2026-10-14T07:00:00+00:00")  # NOW + 25 h: the cache is stale
    _serve(aioclient_mock, content=CHANGED_FEED)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert aioclient_mock.call_count == 0
    assert await _summaries(hass) == cached

    await _step_to(hass, freezer, "2026-10-14T07:00:02+00:00")

    assert aioclient_mock.call_count == 1
    assert "Das Erste: Tagesthemen" in await _summaries(hass)


async def test_missed_daily_slot_refreshes_at_start(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: Any,
    berlin_tz: None,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    freezer.move_to("2026-10-13T16:00:00+00:00")  # 18:00 Berlin, before the 18:15 slot
    entry = await setup_xmltv(FEED, options=DAILY_18_15)
    cached = await _summaries(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)
    freezer.move_to("2026-10-13T16:30:00+00:00")  # the 18:15 slot was missed while HA was down (D-03)
    _serve(aioclient_mock, content=FEED)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert aioclient_mock.call_count == 0
    assert await _summaries(hass) == cached

    await _step_to(hass, freezer, "2026-10-13T16:30:02+00:00")

    assert aioclient_mock.call_count == 1


async def test_fresh_daily_cache_does_not_refresh(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: Any,
    berlin_tz: None,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    freezer.move_to("2026-10-13T16:20:00+00:00")  # 18:20 Berlin, after the 18:15 slot
    entry = await setup_xmltv(FEED, options=DAILY_18_15)
    assert await hass.config_entries.async_unload(entry.entry_id)
    freezer.move_to("2026-10-13T20:00:00+00:00")

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await _step_to(hass, freezer, "2026-10-13T20:00:02+00:00")

    assert entry.state is ConfigEntryState.LOADED
    assert aioclient_mock.call_count == 1
    assert entry.runtime_data.coordinator.next_refresh_at == datetime.fromisoformat("2026-10-14T16:15:00+00:00")


async def test_stale_cache_offline_start_still_loads(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: Any,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED)
    cached = await _summaries(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)
    freezer.move_to("2026-10-14T07:00:00+00:00")
    _serve(aioclient_mock, exc=aiohttp.ClientError())

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED

    await _step_to(hass, freezer, "2026-10-14T07:00:02+00:00")

    coordinator = entry.runtime_data.coordinator
    assert aioclient_mock.call_count == 1
    assert coordinator.last_update_success is False
    assert hass.states.get("calendar.test").state != STATE_UNAVAILABLE
    assert await _summaries(hass) == cached
