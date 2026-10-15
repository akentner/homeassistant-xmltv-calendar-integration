"""Calendar subentry flow: the "Advanced options" step, its storage form and its validation (D-01, D-02)."""

from pathlib import Path
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType

from custom_components.xmltv_calendar.xmltv.settings import (
    KEY_CASE_SENSITIVE,
    KEY_CHANNEL_REGEX,
    KEY_CHANNELS,
    KEY_DESCRIPTION_TEMPLATE,
    KEY_EXCLUDE,
    KEY_EXCLUDE_FIELDS,
    KEY_INCLUDE,
    KEY_INCLUDE_FIELDS,
    KEY_MAX_DURATION,
    KEY_MIN_DURATION,
    KEY_TIME_FROM,
    KEY_TIME_TO,
    KEY_TITLE_TEMPLATE,
    KEY_WEEKDAYS,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry

FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()
NOW = "2026-10-13T06:00:00+00:00"

BASIC = {"name": "Abendschau", KEY_CHANNELS: ["daserste.de"]}
ADVANCED = {
    KEY_INCLUDE_FIELDS: ["title"],
    KEY_EXCLUDE_FIELDS: ["title", "subtitle"],
    KEY_CASE_SENSITIVE: False,
    KEY_TIME_FROM: "19:00:00",
    KEY_TIME_TO: "23:00:00",
    KEY_WEEKDAYS: ["tue"],
    KEY_MIN_DURATION: 10.0,
    KEY_MAX_DURATION: 120.0,
    KEY_TITLE_TEMPLATE: "{title} ({channel})",
}


def _schema_keys(result: Any) -> list[str]:
    return [str(key) for key in result["data_schema"].schema]


async def _summaries(hass: HomeAssistant, entity_id: str) -> list[str]:
    response = await hass.services.async_call(
        "calendar",
        "get_events",
        {"entity_id": entity_id, "start_date_time": "2026-10-13T00:00:00+00:00", "duration": {"hours": 24}},
        blocking=True,
        return_response=True,
    )
    return [event["summary"] for event in response[entity_id]["events"]]


async def test_advanced_options_end_to_end(
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
    assert result["type"] is FlowResultType.FORM
    assert "advanced" in _schema_keys(result)

    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {**BASIC, "advanced": True})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "advanced"

    result = await hass.config_entries.subentries.async_configure(result["flow_id"], ADVANCED)
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "preview"
    assert result["description_placeholders"]["count"] == "1"
    assert result["description_placeholders"]["matches"] == "- Tue 13.10. 20:00 · Das Erste · Tagesschau (Das Erste)"

    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {"next_step_id": "save"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        KEY_CHANNELS: ["daserste.de"],
        KEY_CHANNEL_REGEX: "",
        KEY_INCLUDE: "",
        KEY_EXCLUDE: "",
        KEY_INCLUDE_FIELDS: ["title"],
        KEY_EXCLUDE_FIELDS: ["title", "subtitle"],
        KEY_CASE_SENSITIVE: False,
        KEY_TIME_FROM: "19:00",
        KEY_TIME_TO: "23:00",
        KEY_WEEKDAYS: ["tue"],
        KEY_MIN_DURATION: 10,
        KEY_MAX_DURATION: 120,
        KEY_TITLE_TEMPLATE: "{title} ({channel})",
        KEY_DESCRIPTION_TEMPLATE: "",
    }
    assert type(result["data"][KEY_MIN_DURATION]) is int
    assert type(result["data"][KEY_MAX_DURATION]) is int
    await hass.async_block_till_done()

    assert await _summaries(hass, "calendar.abendschau") == ["Tagesschau (Das Erste)"]
