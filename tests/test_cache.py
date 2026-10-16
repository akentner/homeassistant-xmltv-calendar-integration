"""Disk cache of a URL source: restarts and reloads use it while fresh (SRC-06, D-08, D-09)."""

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from homeassistant.config_entries import ConfigEntryState

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()
NOW = "2026-10-13T06:00:00+00:00"
DOMAIN = "xmltv_calendar"
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
