"""Production-path regressions for matching independently of entity admission."""

from typing import TYPE_CHECKING, Any

from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import async_capture_events

from .test_new_match_event import EVENT, NOW, _refresh, _reload, _stored_seen
from .test_sensor import BASIC_FEED, F1, RACE, SENSOR

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker


async def test_disabled_calendar_keeps_matching(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    aioclient_mock: AiohttpClientMocker,
    hass_storage: dict[str, Any],
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    freezer.move_to(NOW)
    events = async_capture_events(hass, EVENT)
    entry = await setup_xmltv(BASIC_FEED, calendars=F1)
    registry = er.async_get(hass)
    registry.async_update_entity("calendar.f1", disabled_by=er.RegistryEntryDisabler.USER)
    await _reload(hass, entry)

    assert hass.states.get("calendar.f1") is None
    assert hass.states.get(SENSOR).state == "2026-10-13T10:00:00+00:00"
    assert events == []

    await _refresh(hass, aioclient_mock, entry, BASIC_FEED.replace(b"</tv>", RACE))
    state = hass.states.get(SENSOR)
    assert state.state == "2026-10-13T07:00:00+00:00"
    assert state.attributes["summary"] == "Das Erste: Formel 1: Rennen"
    seen = await _stored_seen(hass_storage, entry)
    (uid,) = [key for key in seen if key.startswith("daserste.de-20261013T070000Z-")]
    assert seen[uid] == 1791882000
    assert [event.data for event in events] == [
        {
            "entity_id": "calendar.f1",
            "calendar": "F1",
            "title": "Formel 1: Rennen",
            "summary": "Das Erste: Formel 1: Rennen",
            "channel": "Das Erste",
            "channel_id": "daserste.de",
            "start": "2026-10-13T09:00:00+02:00",
            "end": "2026-10-13T11:00:00+02:00",
            "uid": uid,
        }
    ]
