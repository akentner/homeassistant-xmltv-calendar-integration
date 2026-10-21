"""Next-match sensor: one timestamp sensor per calendar showing the start of the next match (AUT-03, D-01..D-06)."""

from pathlib import Path
from typing import TYPE_CHECKING, Any

from homeassistant.helpers import entity_registry as er

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant

BASIC_FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()
F1 = (("F1", {"channels": ["daserste.de"]}),)


async def test_next_match_sensor_shows_next_start(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    freezer.move_to("2026-10-13T06:00:00+00:00")
    await setup_xmltv(BASIC_FEED, calendars=F1)

    state = hass.states.get("sensor.f1_next_programme")
    assert state is not None
    # Formel 1 starts 12:00 +0200 on Das Erste
    assert state.state == "2026-10-13T10:00:00+00:00"


async def test_sensor_shares_the_calendar_device(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    freezer.move_to("2026-10-13T06:00:00+00:00")
    entry = await setup_xmltv(BASIC_FEED, calendars=F1)
    (subentry_id,) = entry.subentries

    registry = er.async_get(hass)
    sensor = registry.async_get("sensor.f1_next_programme")
    calendar = registry.async_get("calendar.f1")
    assert sensor is not None
    assert calendar is not None
    assert sensor.unique_id == f"{subentry_id}_next_match"
    assert sensor.device_id == calendar.device_id
    assert sensor.disabled_by is None
