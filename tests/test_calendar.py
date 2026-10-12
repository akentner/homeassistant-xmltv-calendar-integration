"""Calendar entity reads: capped get_events, boundary semantics, live state and calendar triggers."""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant

BUSY_DAY = datetime(2026, 10, 13, tzinfo=UTC)


def _busy_feed(channels: int = 60, per_channel: int = 100, minutes: int = 14) -> bytes:
    """Return an XMLTV feed with `channels` x `per_channel` back-to-back programmes on 2026-10-13 (UTC)."""
    parts = ['<?xml version="1.0" encoding="UTF-8"?>', "<tv>"]
    parts.extend(
        f'<channel id="ch{c}.example"><display-name>Channel {c}</display-name></channel>' for c in range(channels)
    )
    for c in range(channels):
        for i in range(per_channel):
            start = BUSY_DAY + timedelta(minutes=i * minutes)
            stop = start + timedelta(minutes=minutes)
            parts.append(
                f'<programme channel="ch{c}.example" start="{start:%Y%m%d%H%M%S} +0000"'
                f' stop="{stop:%Y%m%d%H%M%S} +0000"><title>Show {c}-{i}</title></programme>'
            )
    parts.append("</tv>")
    return "\n".join(parts).encode()


async def _get_events(hass: HomeAssistant, entity_id: str, start: str, hours: float) -> list[dict[str, Any]]:
    response = await hass.services.async_call(
        "calendar",
        "get_events",
        {"entity_id": entity_id, "start_date_time": start, "duration": {"hours": hours}},
        blocking=True,
        return_response=True,
    )
    return response[entity_id]["events"]


async def test_busy_calendar_get_events_is_capped(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    freezer.move_to("2026-10-13T00:00:00+00:00")
    await setup_xmltv(_busy_feed())

    events = await _get_events(hass, "calendar.test", "2026-10-13T00:00:00+00:00", 24)

    assert len(events) == 5000
    starts = [datetime.fromisoformat(event["start"]) for event in events]
    assert starts == sorted(starts)
