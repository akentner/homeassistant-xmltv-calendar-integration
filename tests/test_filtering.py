"""End-to-end filter tests: subentry filter data drives what a calendar shows."""

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant

BASIC_FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()


async def _summaries(hass: HomeAssistant, entity_id: str) -> list[str]:
    response = await hass.services.async_call(
        "calendar",
        "get_events",
        {"entity_id": entity_id, "start_date_time": "2026-10-13T00:00:00+00:00", "duration": {"hours": 24}},
        blocking=True,
        return_response=True,
    )
    return [event["summary"] for event in response[entity_id]["events"]]


async def test_include_pattern_end_to_end(
    hass: HomeAssistant,
    freezer: Any,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    freezer.move_to("2026-10-13T08:00:00+00:00")
    await setup_xmltv(BASIC_FEED, calendars=(("News", {"include": "^Tagesschau$"}),))

    assert await _summaries(hass, "calendar.news") == ["Das Erste: Tagesschau"]
