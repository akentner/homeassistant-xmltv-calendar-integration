"""End-to-end timing tracer: short timestamps with colon offsets and a missing stop."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntryState

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant

FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<tv>
  <channel id="x.de"><display-name>X</display-name></channel>
  <programme channel="x.de" start="202610131200 +02:00"><title>Rennen</title></programme>
  <programme channel="x.de" start="202610131400 +02:00"><title>Analyse</title></programme>
</tv>
"""

# CR-01: every malformed timestamp variant next to two valid programmes
MALFORMED_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<tv>
  <channel id="x.de"><display-name>X</display-name></channel>
  <programme channel="x.de" start="20261013120000 +0200" stop="20261013130000 +0200"><title>Good</title></programme>
  <programme channel="x.de" start="20261013140000 +2500"><title>Offset</title></programme>
  <programme channel="x.de" start="20261013143000 +0099"><title>Minutes</title></programme>
  <programme channel="x.de" start="00010101000000 +0100"><title>Ancient</title></programme>
  <programme channel="x.de" start="99991231233000 -0100" stop="99991231235959 -0100"><title>Future</title></programme>
  <programme channel="x.de" start="99991231233000 +0000"><title>Endless</title></programme>
  <programme channel="x.de" start="20261013150000 +0200" stop="20261013160000 +2500">
    <title>Broken stop</title>
  </programme>
</tv>
"""


async def _events(hass: HomeAssistant) -> list[tuple[str, datetime, datetime]]:
    response = await hass.services.async_call(
        "calendar",
        "get_events",
        {"entity_id": "calendar.test", "start_date_time": "2026-10-13T00:00:00+00:00", "duration": {"hours": 24}},
        blocking=True,
        return_response=True,
    )
    return [
        (event["summary"], datetime.fromisoformat(event["start"]), datetime.fromisoformat(event["end"]))
        for event in response["calendar.test"]["events"]
    ]


async def test_short_timestamp_and_missing_stop_end_to_end(
    hass: HomeAssistant,
    freezer: Any,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    freezer.move_to("2026-10-13T09:00:00+00:00")
    await setup_xmltv(FEED)

    assert await _events(hass) == [
        ("X: Rennen", datetime(2026, 10, 13, 10, tzinfo=UTC), datetime(2026, 10, 13, 12, tzinfo=UTC)),
        ("X: Analyse", datetime(2026, 10, 13, 12, tzinfo=UTC), datetime(2026, 10, 13, 13, tzinfo=UTC)),
    ]


async def test_malformed_timestamps_never_break_the_calendar(
    hass: HomeAssistant,
    freezer: Any,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    freezer.move_to("2026-10-13T09:00:00+00:00")
    entry = await setup_xmltv(MALFORMED_FEED)

    assert entry.state is ConfigEntryState.LOADED
    assert await _events(hass) == [
        ("X: Good", datetime(2026, 10, 13, 10, tzinfo=UTC), datetime(2026, 10, 13, 11, tzinfo=UTC)),
        ("X: Broken stop", datetime(2026, 10, 13, 13, tzinfo=UTC), datetime(2026, 10, 13, 14, tzinfo=UTC)),
    ]
