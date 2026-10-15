"""Calendar subentry edits apply in place: no download, no parse, no reload, siblings untouched (FLT-11, D-04)."""

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()
NOW = "2026-10-13T06:00:00+00:00"


def _subentry_id(entry: MockConfigEntry, title: str) -> str:
    (subentry_id,) = [sid for sid, sub in entry.subentries.items() if sub.title == title]
    return subentry_id


async def _summaries(hass: HomeAssistant, entity_id: str) -> list[str]:
    response = await hass.services.async_call(
        "calendar",
        "get_events",
        {"entity_id": entity_id, "start_date_time": "2026-10-13T00:00:00+00:00", "duration": {"hours": 24}},
        blocking=True,
        return_response=True,
    )
    return [event["summary"] for event in response[entity_id]["events"]]


async def test_data_change_applies_in_place(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(FEED, calendars=(("A", {"include": "tagesschau"}), ("B", {"channels": ["zdf.de"]})))
    a_id = _subentry_id(entry, "A")
    b_id = _subentry_id(entry, "B")
    calls = aioclient_mock.call_count
    runtime = entry.runtime_data
    epg = runtime.coordinator.data
    entity_b = runtime.calendars[b_id]
    b_events = await _summaries(hass, "calendar.b")

    assert hass.config_entries.async_update_subentry(entry, entry.subentries[a_id], data={"include": "formel"})
    await hass.async_block_till_done()

    assert await _summaries(hass, "calendar.a") == ["Das Erste: Formel 1: Großer Preis von Mexiko"]
    assert aioclient_mock.call_count == calls
    assert entry.runtime_data is runtime
    assert runtime.coordinator.data is epg
    assert runtime.calendars[b_id] is entity_b
    assert await _summaries(hass, "calendar.b") == b_events
