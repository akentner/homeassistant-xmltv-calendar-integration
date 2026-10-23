"""Runtime behavior of templates on the Home Assistant surfaces: local time, fallbacks and side effects (D-03, D-05)."""

from typing import TYPE_CHECKING, Any

from pytest_homeassistant_custom_component.common import async_capture_events

from .test_new_match_event import EVENT, NOW, _programme_xml, _refresh
from .test_sensor import SENSOR

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

CHANNELS = (
    b'<?xml version="1.0" encoding="UTF-8"?>\n<tv>\n'
    b'<channel id="daserste.de"><display-name>Das Erste</display-name></channel>\n'
)
# A UTC feed: the wall time in Europe/Berlin (+02:00 in October) differs from the offset written in the feed
LIVE_UTC = _programme_xml("daserste.de", "20261013050000 +0000", "20261013070000 +0000", "Live")
NEXT_UTC = _programme_xml("daserste.de", "20261013100000 +0000", "20261013113000 +0000", "Spaeter")
NEW_UTC = _programme_xml("daserste.de", "20261014120000 +0000", "20261014133000 +0000", "Neu")
UTC_FEED = CHANNELS + LIVE_UTC + NEXT_UTC + b"\n</tv>"
LOCAL_START = "{{ title }} @ {{ start }}"
LOCAL_END = "until {{ end }}"
LOCAL_CALENDAR = (
    ("F1", {"channels": ["daserste.de"], "title_template": LOCAL_START, "description_template": LOCAL_END}),
)


async def _get_events(hass: HomeAssistant, entity_id: str) -> list[dict[str, Any]]:
    response = await hass.services.async_call(
        "calendar",
        "get_events",
        {"entity_id": entity_id, "start_date_time": "2026-10-12T00:00:00+00:00", "duration": {"hours": 72}},
        blocking=True,
        return_response=True,
    )
    return response[entity_id]["events"]


async def test_start_variable_is_local_time_everywhere(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    freezer.move_to(NOW)
    events = async_capture_events(hass, EVENT)
    entry = await setup_xmltv(UTC_FEED, calendars=LOCAL_CALENDAR)

    # get_events: 10:00 UTC is 12:00 in Berlin, with the +02:00 offset instead of the feed's +00:00
    listed = await _get_events(hass, "calendar.f1")
    assert [event["summary"] for event in listed] == [
        "Live @ 2026-10-13 07:00:00+02:00",
        "Spaeter @ 2026-10-13 12:00:00+02:00",
    ]
    assert [event["description"] for event in listed] == [
        "until 2026-10-13 09:00:00+02:00",
        "until 2026-10-13 13:30:00+02:00",
    ]
    # The live event of the calendar entity (Live is airing at 06:00 UTC)
    assert hass.states.get("calendar.f1").attributes["message"] == "Live @ 2026-10-13 07:00:00+02:00"
    # The next-match sensor summary
    assert hass.states.get(SENSOR).attributes["summary"] == "Spaeter @ 2026-10-13 12:00:00+02:00"

    # The summary of the new-match event fired by a refresh that adds a UTC programme
    await _refresh(hass, aioclient_mock, entry, CHANNELS + LIVE_UTC + NEXT_UTC + NEW_UTC + b"\n</tv>")
    assert [event.data["summary"] for event in events] == ["Neu @ 2026-10-14 14:00:00+02:00"]
    assert events[0].data["start"] == "2026-10-14T14:00:00+02:00"
