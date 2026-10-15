"""Calendar subentry flow: the "Advanced options" step, its storage form and its validation (D-01, D-02)."""

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType

from custom_components.xmltv_calendar.const import (
    CONF_CASE_SENSITIVE,
    CONF_CHANNEL_REGEX,
    CONF_CHANNELS,
    CONF_DESCRIPTION_TEMPLATE,
    CONF_EXCLUDE,
    CONF_EXCLUDE_FIELDS,
    CONF_INCLUDE,
    CONF_INCLUDE_FIELDS,
    CONF_MAX_DURATION,
    CONF_MIN_DURATION,
    CONF_TIME_FROM,
    CONF_TIME_TO,
    CONF_TITLE_TEMPLATE,
    CONF_WEEKDAYS,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry

FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()
NOW = "2026-10-13T06:00:00+00:00"

BASIC = {"name": "Abendschau", CONF_CHANNELS: ["daserste.de"]}
ADVANCED = {
    CONF_INCLUDE_FIELDS: ["title"],
    CONF_EXCLUDE_FIELDS: ["title", "subtitle"],
    CONF_CASE_SENSITIVE: False,
    CONF_TIME_FROM: "19:00:00",
    CONF_TIME_TO: "23:00:00",
    CONF_WEEKDAYS: ["tue"],
    CONF_MIN_DURATION: 10.0,
    CONF_MAX_DURATION: 120.0,
    CONF_TITLE_TEMPLATE: "{title} ({channel})",
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
        CONF_CHANNELS: ["daserste.de"],
        CONF_CHANNEL_REGEX: "",
        CONF_INCLUDE: "",
        CONF_EXCLUDE: "",
        CONF_INCLUDE_FIELDS: ["title"],
        CONF_EXCLUDE_FIELDS: ["title", "subtitle"],
        CONF_CASE_SENSITIVE: False,
        CONF_TIME_FROM: "19:00",
        CONF_TIME_TO: "23:00",
        CONF_WEEKDAYS: ["tue"],
        CONF_MIN_DURATION: 10,
        CONF_MAX_DURATION: 120,
        CONF_TITLE_TEMPLATE: "{title} ({channel})",
        CONF_DESCRIPTION_TEMPLATE: "",
    }
    assert type(result["data"][CONF_MIN_DURATION]) is int
    assert type(result["data"][CONF_MAX_DURATION]) is int
    await hass.async_block_till_done()

    assert await _summaries(hass, "calendar.abendschau") == ["Tagesschau (Das Erste)"]


async def _advanced_form(hass: HomeAssistant, entry: MockConfigEntry) -> Any:
    """Start a new calendar flow and submit the basic form with the checkbox set: the advanced form."""
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "calendar"), context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {**BASIC, "advanced": True})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "advanced"
    return result


def _suggested(result: Any, name: str) -> Any:
    """Return the suggested value of a form field, or None when the field has none."""
    for key in result["data_schema"].schema:
        if key == name:
            return (key.description or {}).get("suggested_value")
    msg = f"{name} not in form"
    raise AssertionError(msg)


def _without(*keys: str, **changes: Any) -> dict[str, Any]:
    """Return the valid advanced input with keys removed (cleared fields) and values changed."""
    return {key: value for key, value in ADVANCED.items() if key not in keys} | changes


@pytest.mark.parametrize(
    ("user_input", "errors"),
    [
        pytest.param(
            _without(**{CONF_INCLUDE_FIELDS: []}), {CONF_INCLUDE_FIELDS: "fields_required"}, id="include_fields_empty"
        ),
        pytest.param(
            _without(**{CONF_EXCLUDE_FIELDS: []}), {CONF_EXCLUDE_FIELDS: "fields_required"}, id="exclude_fields_empty"
        ),
        pytest.param(
            _without(CONF_TIME_TO, **{CONF_TIME_FROM: "22:00:00"}),
            {CONF_TIME_TO: "time_incomplete"},
            id="time_to_missing",
        ),
        pytest.param(_without(CONF_TIME_FROM), {CONF_TIME_FROM: "time_incomplete"}, id="time_from_missing"),
        pytest.param(
            _without(**{CONF_TIME_FROM: "22:00", CONF_TIME_TO: "22:00:00"}),
            {CONF_TIME_TO: "time_equal"},
            id="time_equal",
        ),
        pytest.param(
            _without(**{CONF_MIN_DURATION: 90.0, CONF_MAX_DURATION: 30.0}),
            {CONF_MAX_DURATION: "duration_order"},
            id="duration_order",
        ),
        pytest.param(
            _without(**{CONF_TITLE_TEMPLATE: "{title"}), {CONF_TITLE_TEMPLATE: "invalid_template"}, id="title_braces"
        ),
        pytest.param(
            _without(**{CONF_TITLE_TEMPLATE: "{description}"}),
            {CONF_TITLE_TEMPLATE: "unknown_placeholder"},
            id="title_description_field",
        ),
        pytest.param(
            _without(**{CONF_TITLE_TEMPLATE: "{title:>9}"}),
            {CONF_TITLE_TEMPLATE: "unknown_placeholder"},
            id="title_format_spec",
        ),
        pytest.param(
            _without(**{CONF_DESCRIPTION_TEMPLATE: "{channel.x}"}),
            {CONF_DESCRIPTION_TEMPLATE: "unknown_placeholder"},
            id="description_attribute",
        ),
    ],
)
async def test_advanced_validation(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
    user_input: dict[str, Any],
    errors: dict[str, str],
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(FEED, calendars=())
    result = await _advanced_form(hass, entry)

    result = await hass.config_entries.subentries.async_configure(result["flow_id"], user_input)

    assert result.get("errors") == errors
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "advanced"
    # Nothing typed is lost: every submitted value comes back as the suggested value
    for key, value in user_input.items():
        assert _suggested(result, key) == value
    assert not entry.subentries


async def test_unknown_placeholder_names_the_offending_text(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(FEED, calendars=())
    result = await _advanced_form(hass, entry)

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], _without(**{CONF_TITLE_TEMPLATE: "{foo}"})
    )

    assert result.get("errors") == {CONF_TITLE_TEMPLATE: "unknown_placeholder"}
    assert result["description_placeholders"]["template_error"] == "{foo}"
    assert "pattern" not in result["description_placeholders"]
    assert "error" not in result["description_placeholders"]


async def test_invalid_template_shows_the_parse_error(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(FEED, calendars=())
    result = await _advanced_form(hass, entry)

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], _without(**{CONF_TITLE_TEMPLATE: "{title"})
    )

    assert result.get("errors") == {CONF_TITLE_TEMPLATE: "invalid_template"}
    assert result["description_placeholders"]["template_error"]  # the parser message; its wording is not asserted


async def test_both_templates_invalid_get_their_own_errors(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(FEED, calendars=())
    result = await _advanced_form(hass, entry)

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], _without(**{CONF_TITLE_TEMPLATE: "{foo}", CONF_DESCRIPTION_TEMPLATE: "{bar[0]}"})
    )

    assert result.get("errors") == {
        CONF_TITLE_TEMPLATE: "unknown_placeholder",
        CONF_DESCRIPTION_TEMPLATE: "unknown_placeholder",
    }
    assert result["description_placeholders"]["template_error"] == "{foo}"
    assert "pattern" not in result["description_placeholders"]
    assert "error" not in result["description_placeholders"]


@pytest.mark.parametrize(
    "user_input",
    [
        pytest.param(_without(**{CONF_MIN_DURATION: 30.0, CONF_MAX_DURATION: 30.0}), id="equal_durations"),
        pytest.param(_without(**{CONF_DESCRIPTION_TEMPLATE: "{description}"}), id="description_placeholder"),
    ],
)
async def test_valid_edge_input_reaches_the_preview(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
    user_input: dict[str, Any],
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(FEED, calendars=())
    result = await _advanced_form(hass, entry)

    result = await hass.config_entries.subentries.async_configure(result["flow_id"], user_input)

    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] in {"preview", "preview_empty"}


async def test_cleared_time_window_is_stored_as_none_on_edit(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
) -> None:
    freezer.move_to(NOW)
    stored = {CONF_CHANNELS: ["daserste.de"], CONF_TIME_FROM: "20:00", CONF_TIME_TO: "23:00"}
    entry = await setup_xmltv(FEED, calendars=(("Abend", stored),))
    (subentry_id,) = entry.subentries

    result = await entry.start_subentry_reconfigure_flow(hass, subentry_id)
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"name": "Abend", CONF_CHANNELS: ["daserste.de"], "advanced": True}
    )
    assert result["step_id"] == "advanced"
    assert _suggested(result, CONF_TIME_FROM) == "20:00:00"
    assert _suggested(result, CONF_TIME_TO) == "23:00:00"

    # The user empties both time fields: the keys are absent from the submit (D-20)
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {CONF_INCLUDE_FIELDS: ["title", "subtitle"], CONF_EXCLUDE_FIELDS: ["title", "subtitle"]}
    )
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {"next_step_id": "save"})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()

    data = entry.subentries[subentry_id].data
    assert data[CONF_TIME_FROM] is None
    assert data[CONF_TIME_TO] is None
    assert "advanced" not in data
