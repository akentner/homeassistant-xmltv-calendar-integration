"""Feed ingestion through Home Assistant: gzip detected by content, truncated refreshes keep the previous data."""

import gzip
from pathlib import Path
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntryState

from .conftest import FEED_URL

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

BASIC_FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()
OCTET_STREAM = {"content-type": "application/octet-stream"}


async def _get_events(hass: HomeAssistant, entity_id: str, start: str, hours: float) -> list[dict[str, Any]]:
    response = await hass.services.async_call(
        "calendar",
        "get_events",
        {"entity_id": entity_id, "start_date_time": start, "duration": {"hours": hours}},
        blocking=True,
        return_response=True,
    )
    return response[entity_id]["events"]


async def test_gzip_behind_xml_url_end_to_end(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: Any,
    berlin_tz: None,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    freezer.move_to("2026-10-13T00:00:00+00:00")
    payload = gzip.compress(BASIC_FEED)
    # Registered before setup_xmltv's own mock, so this response (gzip body, generic content type) wins
    aioclient_mock.get(FEED_URL, content=payload, headers=OCTET_STREAM)

    entry = await setup_xmltv(payload, calendars=(("All", {}),))

    assert FEED_URL.endswith(".xml")
    assert entry.state is ConfigEntryState.LOADED
    events = await _get_events(hass, "calendar.all", "2026-10-13T00:00:00+02:00", 24)
    assert [(event["start"], event["summary"]) for event in events] == [
        ("2026-10-13T12:00:00+02:00", "Das Erste: Formel 1: Großer Preis von Mexiko"),
        ("2026-10-13T12:00:00+02:00", "ZDF: heute"),
        ("2026-10-13T19:00:00+02:00", "ZDF: heute"),
        ("2026-10-13T20:00:00+02:00", "Das Erste: Tagesschau"),
    ]


async def test_refresh_with_truncated_gzip_keeps_previous_data(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: Any,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    freezer.move_to("2026-10-13T00:00:00+00:00")
    payload = gzip.compress(BASIC_FEED)
    entry = await setup_xmltv(payload)
    assert entry.state is ConfigEntryState.LOADED
    coordinator = entry.runtime_data.coordinator
    previous = coordinator.data

    aioclient_mock.clear_requests()
    aioclient_mock.get(FEED_URL, content=payload[: len(payload) // 2], headers=OCTET_STREAM)
    await coordinator.async_refresh()

    assert aioclient_mock.call_count == 1
    assert coordinator.last_update_success is False
    assert coordinator.last_exception.translation_key == "invalid_feed"
    assert coordinator.data is previous
