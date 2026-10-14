"""Calendar entity reads: capped get_events, boundary semantics, live state and calendar triggers."""

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed, async_mock_service

from custom_components.xmltv_calendar import calendar as calendar_module
from custom_components.xmltv_calendar.calendar import build_events
from custom_components.xmltv_calendar.xmltv.model import Channel, Programme
from custom_components.xmltv_calendar.xmltv.window import MatchIndex

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

BUSY_DAY = datetime(2026, 10, 13, tzinfo=UTC)
BASIC_FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()
NO_PROGRAMMES_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<tv>
  <channel id="daserste.de"><display-name>Das Erste</display-name></channel>
  <channel id="zdf.de"><display-name>ZDF</display-name></channel>
</tv>
"""


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


def _programme(start: datetime, stop: datetime, title: str) -> Programme:
    return Programme(
        channel_id="daserste.de",
        start=start,
        stop=stop,
        titles=(title,),
        sub_titles=(),
        description=None,
        categories=(),
        episode=None,
    )


def test_build_events_skips_invalid(caplog: pytest.LogCaptureFixture) -> None:
    good = _programme(BUSY_DAY, BUSY_DAY + timedelta(hours=1), "Good")
    # Constructed directly, bypassing normalize: CalendarEvent rejects end < start
    bad = _programme(BUSY_DAY + timedelta(hours=2), BUSY_DAY + timedelta(hours=1), "Bad")
    channels = {"daserste.de": Channel(id="daserste.de", display_name="Das Erste")}

    with caplog.at_level(logging.DEBUG, logger="custom_components.xmltv_calendar"):
        events = build_events([good, bad], channels)

    assert [event.summary for event in events] == ["Das Erste: Good"]
    assert "daserste.de" in caplog.text


FAR_START = datetime(9999, 12, 31, 23, tzinfo=UTC)
CHANNELS = {"daserste.de": Channel(id="daserste.de", display_name="Das Erste")}


async def test_build_events_skips_out_of_range_programme(
    hass: HomeAssistant, berlin_tz: None, caplog: pytest.LogCaptureFixture
) -> None:
    good = _programme(BUSY_DAY, BUSY_DAY + timedelta(hours=1), "Good")
    # Under Europe/Berlin, dt_util.as_local of this instant overflows datetime's range (CR-01)
    far = _programme(FAR_START, FAR_START + timedelta(minutes=30), "Far future")

    with caplog.at_level(logging.DEBUG, logger="custom_components.xmltv_calendar"):
        events = build_events([good, far], CHANNELS)

    assert [event.summary for event in events] == ["Das Erste: Good"]
    assert "daserste.de" in caplog.text


def test_build_events_skips_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    good = _programme(BUSY_DAY, BUSY_DAY + timedelta(hours=1), "Good")
    bad = _programme(BUSY_DAY + timedelta(hours=2), BUSY_DAY + timedelta(hours=3), "Bad")
    real = calendar_module._to_event

    def flaky(programme: Programme, channels: Any) -> Any:
        if programme.title == "Bad":
            msg = "boom"
            raise ValueError(msg)
        return real(programme, channels)

    monkeypatch.setattr(calendar_module, "_to_event", flaky)

    assert [event.summary for event in build_events([good, bad], CHANNELS)] == ["Das Erste: Good"]


async def test_event_property_skips_out_of_range_match(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    freezer.move_to("2026-10-13T00:00:00+00:00")
    entry = await setup_xmltv(BASIC_FEED)
    entity = next(iter(entry.runtime_data.calendars.values()))
    far = _programme(FAR_START, FAR_START + timedelta(minutes=30), "Far future")
    entity._index = MatchIndex((far,))

    assert entity.event is None


async def _step_to(hass: HomeAssistant, freezer: Any, iso: str) -> None:
    freezer.move_to(iso)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def test_state_turns_on_and_off_without_refresh(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    freezer.move_to("2026-10-13T09:59:00+00:00")
    await setup_xmltv(BASIC_FEED, calendars=(("Formel 1", {"channels": ["daserste.de"]}),))
    calls = aioclient_mock.call_count

    state = hass.states.get("calendar.formel_1")
    assert state is not None
    assert state.state == "off"

    # Formel 1 airs 10:00-11:30 UTC on Das Erste
    await _step_to(hass, freezer, "2026-10-13T10:00:00+00:00")
    state = hass.states.get("calendar.formel_1")
    assert state.state == "on"
    assert state.attributes["message"] == "Das Erste: Formel 1: Großer Preis von Mexiko"
    assert state.attributes["location"] == "Das Erste"
    assert dt_util.as_utc(dt_util.parse_datetime(state.attributes["start_time"], raise_on_error=True)) == datetime(
        2026, 10, 13, 10, tzinfo=UTC
    )
    assert dt_util.as_utc(dt_util.parse_datetime(state.attributes["end_time"], raise_on_error=True)) == datetime(
        2026, 10, 13, 11, 30, tzinfo=UTC
    )

    # At its stop the state goes off and the attributes move on to the next match (Tagesschau)
    await _step_to(hass, freezer, "2026-10-13T11:30:00+00:00")
    state = hass.states.get("calendar.formel_1")
    assert state.state == "off"
    assert state.attributes["message"] == "Das Erste: Tagesschau"

    assert aioclient_mock.call_count == calls


async def test_start_offset_and_end_triggers_fire(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    # 09:45 is an aligned 15-minute boundary; the programme ends 11:30, exactly on a trigger-window boundary
    freezer.move_to("2026-10-13T09:45:00+00:00")
    await setup_xmltv(BASIC_FEED, calendars=(("F1", {"channels": ["daserste.de"]}),))
    calls = async_mock_service(hass, "test", "automation")
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": [
                {
                    "triggers": [
                        {"trigger": "calendar", "event": "start", "offset": "-0:05:00", "entity_id": "calendar.f1"}
                    ],
                    "actions": [
                        {"action": "test.automation", "data": {"summary": "{{ trigger.calendar_event.summary }}"}}
                    ],
                },
                {
                    "triggers": [{"trigger": "calendar", "event": "end", "entity_id": "calendar.f1"}],
                    "actions": [
                        {
                            "action": "test.automation",
                            "data": {
                                "location": "{{ trigger.calendar_event.location }}",
                                "end": "{{ trigger.calendar_event.end }}",
                            },
                        }
                    ],
                },
            ]
        },
    )

    fired: list[tuple[datetime, dict[str, Any]]] = []
    now = datetime(2026, 10, 13, 9, 45, tzinfo=UTC)
    # Step one minute at a time: coarse jumps skip trigger windows
    while now < datetime(2026, 10, 13, 11, 40, tzinfo=UTC):
        now += timedelta(minutes=1)
        await _step_to(hass, freezer, now.isoformat())
        fired.extend((now, dict(call.data)) for call in calls[len(fired) :])

    await hass.services.async_call("automation", "turn_off", {"entity_id": "all"}, blocking=True)

    starts = [(at, data) for at, data in fired if "summary" in data]
    ends = [(at, data) for at, data in fired if "location" in data]
    assert starts == [
        (datetime(2026, 10, 13, 9, 55, tzinfo=UTC), {"summary": "Das Erste: Formel 1: Großer Preis von Mexiko"})
    ]
    # The 11:30 window refresh schedules the already-due alarm, which runs on the next time tick
    assert len(ends) == 1
    fired_at, data = ends[0]
    assert data["location"] == "Das Erste"
    assert dt_util.as_utc(dt_util.parse_datetime(data["end"], raise_on_error=True)) == datetime(
        2026, 10, 13, 11, 30, tzinfo=UTC
    )
    assert datetime(2026, 10, 13, 11, 30, tzinfo=UTC) <= fired_at <= datetime(2026, 10, 13, 11, 31, tzinfo=UTC)


@pytest.mark.parametrize(
    ("feed", "data"),
    [
        pytest.param(BASIC_FEED, {"channels": ["absent.de"]}, id="channel-not-in-feed"),
        pytest.param(NO_PROGRAMMES_FEED, {}, id="feed-without-programmes"),
    ],
)
async def test_calendar_with_no_matches(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    setup_xmltv: Callable[..., Awaitable[Any]],
    feed: bytes,
    data: dict[str, Any],
) -> None:
    freezer.move_to("2026-10-13T10:30:00+00:00")
    entry = await setup_xmltv(feed, calendars=(("Empty", data),))

    assert entry.state is ConfigEntryState.LOADED
    assert await _get_events(hass, "calendar.empty", "2026-10-13T00:00:00+00:00", 24) == []
    state = hass.states.get("calendar.empty")
    assert state is not None
    assert state.state == "off"
