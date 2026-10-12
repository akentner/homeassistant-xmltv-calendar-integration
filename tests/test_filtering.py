"""End-to-end filter tests: subentry filter data drives what a calendar shows."""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    import pytest
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


async def test_missing_channel_warning_once_per_refresh(
    hass: HomeAssistant,
    freezer: Any,
    caplog: pytest.LogCaptureFixture,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    freezer.move_to("2026-10-13T08:00:00+00:00")
    entry = await setup_xmltv(BASIC_FEED, calendars=(("Mixed", {"channels": ["gone.de", "zdf.de"]}),))

    def missing_warnings() -> list[logging.LogRecord]:
        return [r for r in caplog.records if r.levelno == logging.WARNING and "gone.de" in r.getMessage()]

    assert len(missing_warnings()) == 1

    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()
    assert len(missing_warnings()) == 2

    assert await _summaries(hass, "calendar.mixed") == ["ZDF: heute", "ZDF: heute"]
