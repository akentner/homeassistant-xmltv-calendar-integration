"""Title and description templates shape the events a calendar shows (EVT-03, EVT-04)."""

from pathlib import Path
from typing import TYPE_CHECKING, Any

from custom_components.xmltv_calendar.xmltv.settings import KEY_CHANNELS, KEY_DESCRIPTION_TEMPLATE, KEY_TITLE_TEMPLATE

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()
NOW = "2026-10-13T06:00:00+00:00"
DETAILED = b"""<?xml version="1.0" encoding="UTF-8"?>
<tv>
  <channel id="daserste.de"><display-name>Das Erste</display-name></channel>
  <programme channel="daserste.de" start="20261013201500 +0200" stop="20261013214500 +0200">
    <title>Tatort</title>
    <sub-title>Der Fall</sub-title>
    <desc>Kommissarin ermittelt.</desc>
    <category>Krimi</category>
    <category>Reihe</category>
    <episode-num system="onscreen">S01E04</episode-num>
  </programme>
</tv>
"""


async def _events(hass: HomeAssistant, entity_id: str) -> list[dict[str, Any]]:
    response = await hass.services.async_call(
        "calendar",
        "get_events",
        {"entity_id": entity_id, "start_date_time": "2026-10-13T00:00:00+00:00", "duration": {"hours": 24}},
        blocking=True,
        return_response=True,
    )
    return response[entity_id]["events"]


async def _summaries(hass: HomeAssistant, entity_id: str) -> list[str]:
    return [event["summary"] for event in await _events(hass, entity_id)]


async def test_title_template_end_to_end(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
) -> None:
    freezer.move_to(NOW)
    await setup_xmltv(
        FEED, calendars=(("Erste", {KEY_CHANNELS: ["daserste.de"], KEY_TITLE_TEMPLATE: "{title} – {subtitle}"}),)
    )

    assert await _summaries(hass, "calendar.erste") == [
        "Formel 1: Großer Preis von Mexiko – Qualifying",
        "Tagesschau",
    ]


async def test_template_edit_applies_in_place(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(FEED, calendars=(("Erste", {KEY_CHANNELS: ["daserste.de"]}),))
    (subentry,) = entry.subentries.values()
    calls = aioclient_mock.call_count

    assert hass.config_entries.async_update_subentry(
        entry, subentry, data={KEY_CHANNELS: ["daserste.de"], KEY_TITLE_TEMPLATE: "{title} ({channel})"}
    )
    await hass.async_block_till_done()

    assert await _summaries(hass, "calendar.erste") == [
        "Formel 1: Großer Preis von Mexiko (Das Erste)",
        "Tagesschau (Das Erste)",
    ]
    assert aioclient_mock.call_count == calls


async def test_default_description_end_to_end(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
) -> None:
    freezer.move_to(NOW)
    await setup_xmltv(DETAILED, calendars=(("Krimi", {}),))

    (event,) = await _events(hass, "calendar.krimi")
    assert event["summary"] == "Das Erste: Tatort"
    assert event["description"] == "Der Fall\nEpisode: S01E04\nCategories: Krimi, Reihe\n\nKommissarin ermittelt."


async def test_description_template_end_to_end(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
) -> None:
    freezer.move_to(NOW)
    await setup_xmltv(DETAILED, calendars=(("Krimi", {KEY_DESCRIPTION_TEMPLATE: "{description}"}),))

    (event,) = await _events(hass, "calendar.krimi")
    assert event["description"] == "Kommissarin ermittelt."
