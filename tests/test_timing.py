"""End-to-end timing tracer: short timestamps with colon offsets and a missing stop."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

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


async def test_short_timestamp_and_missing_stop_end_to_end(
    hass: HomeAssistant,
    freezer: Any,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    freezer.move_to("2026-10-13T09:00:00+00:00")
    await setup_xmltv(FEED)

    response = await hass.services.async_call(
        "calendar",
        "get_events",
        {"entity_id": "calendar.test", "start_date_time": "2026-10-13T00:00:00+00:00", "duration": {"hours": 24}},
        blocking=True,
        return_response=True,
    )
    events = [
        (event["summary"], datetime.fromisoformat(event["start"]), datetime.fromisoformat(event["end"]))
        for event in response["calendar.test"]["events"]
    ]
    assert events == [
        ("X: Rennen", datetime(2026, 10, 13, 10, tzinfo=UTC), datetime(2026, 10, 13, 12, tzinfo=UTC)),
        ("X: Analyse", datetime(2026, 10, 13, 12, tzinfo=UTC), datetime(2026, 10, 13, 13, tzinfo=UTC)),
    ]
