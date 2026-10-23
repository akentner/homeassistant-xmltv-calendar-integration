"""Title and description templates shape the events a calendar shows (EVT-03, EVT-04)."""

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from homeassistant.components.calendar.const import DATA_COMPONENT
from homeassistant.config_entries import SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType

from custom_components.xmltv_calendar.config_flow import XmltvConfigFlow
from custom_components.xmltv_calendar.const import CONF_ADVANCED
from custom_components.xmltv_calendar.xmltv.settings import (
    KEY_CHANNELS,
    KEY_DESCRIPTION_TEMPLATE,
    KEY_EXCLUDE_FIELDS,
    KEY_INCLUDE_FIELDS,
    KEY_TITLE_TEMPLATE,
    has_advanced,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    import pytest
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()
NOW = "2026-10-13T06:00:00+00:00"
# Strips the redundant "Formel 1" prefix from a title (D-07)
FORMULA_ONE = "{{ channel }}: {{ title | regex_replace('^Formel ?1:? ?', '') }}"
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
        FEED,
        calendars=(("Erste", {KEY_CHANNELS: ["daserste.de"], KEY_TITLE_TEMPLATE: "{{ title }} – {{ subtitle }}"}),),
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
        entry, subentry, data={KEY_CHANNELS: ["daserste.de"], KEY_TITLE_TEMPLATE: "{{ title }} ({{ channel }})"}
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
    await setup_xmltv(DETAILED, calendars=(("Krimi", {KEY_DESCRIPTION_TEMPLATE: "{{ description }}"}),))

    (event,) = await _events(hass, "calendar.krimi")
    assert event["description"] == "Kommissarin ermittelt."


async def _uids(hass: HomeAssistant, entity_id: str) -> list[str | None]:
    entity = hass.data[DATA_COMPONENT].get_entity(entity_id)
    assert entity is not None
    events = await entity.async_get_events(
        hass, datetime.fromisoformat("2026-10-13T00:00:00+00:00"), datetime.fromisoformat("2026-10-14T00:00:00+00:00")
    )
    return [event.uid for event in events]


async def test_formula_one_prefix_stripped_end_to_end(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
) -> None:
    """Tracer: a stored Jinja title template reaches calendar.get_events, the feed and the UIDs stay untouched."""
    freezer.move_to(NOW)
    await setup_xmltv(
        FEED,
        calendars=(
            ("Erste", {KEY_CHANNELS: ["daserste.de"], KEY_TITLE_TEMPLATE: FORMULA_ONE}),
            ("Plain", {KEY_CHANNELS: ["daserste.de"]}),
        ),
    )

    assert await _summaries(hass, "calendar.erste") == ["Das Erste: Großer Preis von Mexiko", "Das Erste: Tagesschau"]
    # The feed title is unchanged and the UIDs hash it, so they equal the default-template UIDs
    assert await _summaries(hass, "calendar.plain") == [
        "Das Erste: Formel 1: Großer Preis von Mexiko",
        "Das Erste: Tagesschau",
    ]
    uids = await _uids(hass, "calendar.erste")
    assert len(uids) == 2
    assert uids == await _uids(hass, "calendar.plain")


async def test_formula_one_template_through_the_calendar_flow(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
    berlin_tz: None,
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(FEED, calendars=())

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "calendar"), context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"name": "Formel", KEY_CHANNELS: ["daserste.de"], CONF_ADVANCED: True}
    )
    assert result["step_id"] == "advanced"

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            KEY_INCLUDE_FIELDS: ["title"],
            KEY_EXCLUDE_FIELDS: ["title"],
            KEY_TITLE_TEMPLATE: FORMULA_ONE,
        },
    )
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "preview"
    first_line = result["description_placeholders"]["matches"].splitlines()[0]
    assert first_line == "- Tue 13.10. 12:00 · Das Erste · Das Erste: Großer Preis von Mexiko"

    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {"next_step_id": "save"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][KEY_TITLE_TEMPLATE] == FORMULA_ONE  # stored unchanged
    await hass.async_block_till_done()

    assert await _summaries(hass, "calendar.formel") == [
        "Das Erste: Großer Preis von Mexiko",
        "Das Erste: Tagesschau",
    ]


async def test_legacy_stored_template_falls_back_with_one_warning(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
    caplog: pytest.LogCaptureFixture,
) -> None:
    freezer.move_to(NOW)
    legacy = "{title} - {subtitle}"
    with caplog.at_level(logging.WARNING):
        await setup_xmltv(
            FEED,
            calendars=(
                ("Alt", {KEY_CHANNELS: ["daserste.de"], KEY_TITLE_TEMPLATE: legacy}),
                ("Standard", {KEY_CHANNELS: ["daserste.de"], KEY_TITLE_TEMPLATE: "{channel}: {title}"}),
            ),
        )
        assert await _summaries(hass, "calendar.alt") == [
            "Das Erste: Formel 1: Großer Preis von Mexiko",
            "Das Erste: Tagesschau",
        ]

    warnings = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING and "template" in r.getMessage()]
    assert len(warnings) == 1  # the exact legacy default of "Standard" is normalized silently
    assert "Alt" in warnings[0]
    assert "legacy_placeholder" in warnings[0]
    assert legacy not in warnings[0]
    assert "Standard" not in warnings[0]
    assert await _summaries(hass, "calendar.standard") == await _summaries(hass, "calendar.alt")
    assert has_advanced({KEY_TITLE_TEMPLATE: "{channel}: {title}"}) is False


def test_the_config_flow_version_is_unchanged() -> None:
    # A10: legacy text is handled at read time, nothing is migrated
    assert XmltvConfigFlow.VERSION == 1
