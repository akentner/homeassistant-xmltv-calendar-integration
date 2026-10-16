"""Per-source timezone options end to end: offset-less timestamps as local time, offset correction (SRC-10)."""

from typing import TYPE_CHECKING, Any

import pytest

from custom_components.xmltv_calendar.const import CONF_NAIVE_TIMEZONE, CONF_REFRESH_HOURS, NAIVE_TZ_LOCAL

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry

NOW = "2026-10-13T06:00:00+00:00"  # 08:00 in Europe/Berlin
pytestmark = [pytest.mark.freeze_time(NOW), pytest.mark.usefixtures("berlin_tz")]

NAIVE_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<tv>
  <channel id="daserste.de"><display-name>Das Erste</display-name></channel>
  <programme channel="daserste.de" start="20261013200000" stop="20261013201500"><title>Tagesschau</title></programme>
</tv>
"""


async def _events(hass: HomeAssistant) -> list[dict[str, Any]]:
    response = await hass.services.async_call(
        "calendar",
        "get_events",
        {"entity_id": "calendar.test", "start_date_time": "2026-10-13T00:00:00+02:00", "duration": {"hours": 24}},
        blocking=True,
        return_response=True,
    )
    return response["calendar.test"]["events"]


async def test_naive_local_timestamps_end_to_end(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    await setup_xmltv(NAIVE_FEED, options={CONF_REFRESH_HOURS: 24, CONF_NAIVE_TIMEZONE: NAIVE_TZ_LOCAL})

    events = await _events(hass)
    assert [(event["start"], event["end"]) for event in events] == [
        ("2026-10-13T20:00:00+02:00", "2026-10-13T20:15:00+02:00")
    ]


async def test_naive_timestamps_stay_utc_by_default(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    await setup_xmltv(NAIVE_FEED)

    events = await _events(hass)
    assert [(event["start"], event["end"]) for event in events] == [
        ("2026-10-13T22:00:00+02:00", "2026-10-13T22:15:00+02:00")
    ]
