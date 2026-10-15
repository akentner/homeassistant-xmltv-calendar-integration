"""Calendar subentry flow: the "Add calendar" form, its filters and their validation."""

from typing import TYPE_CHECKING, Any

import pytest
from homeassistant.config_entries import SOURCE_USER, ConfigEntryState
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.xmltv_calendar.xmltv.settings import with_defaults

from .conftest import DOMAIN, FEED_URL, complete_calendar_flow

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

NOW = "2026-10-13T06:00:00+00:00"
DAY_START = "2026-10-13T00:00:00+00:00"

CHANNELS = """
  <channel id="daserste.de"><display-name>Das Erste</display-name></channel>
  <channel id="zdf.de"><display-name>ZDF</display-name></channel>
"""


def _feed(programmes: str, channels: str = CHANNELS) -> bytes:
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<tv>{channels}{programmes}</tv>\n'.encode()


def _programme(channel: str, start: str, stop: str, title: str) -> str:
    return (
        f'<programme channel="{channel}" start="{start} +0000" stop="{stop} +0000"><title>{title}</title></programme>\n'
    )


# basic.xml-style feed with exactly two motorsport programmes, one per channel
MOTORSPORT_FEED = _feed(
    _programme("daserste.de", "20261013120000", "20261013140000", "Formel 1: Rennen")
    + _programme("daserste.de", "20261013180000", "20261013181500", "Tagesschau")
    + _programme("zdf.de", "20261013150000", "20261013160000", "Formula 1 Highlights")
    + _programme("zdf.de", "20261013170000", "20261013171500", "heute")
)


def _schema_keys(result: Any) -> list[str]:
    return [str(key) for key in result["data_schema"].schema]


def _schema_key(result: Any, name: str) -> Any:
    for key in result["data_schema"].schema:
        if key == name:
            return key
    msg = f"{name} not in form"
    raise AssertionError(msg)


async def _start_flow(hass: HomeAssistant, entry: MockConfigEntry) -> Any:
    return await hass.config_entries.subentries.async_init(
        (entry.entry_id, "calendar"), context={"source": SOURCE_USER}
    )


async def _submit(hass: HomeAssistant, entry: MockConfigEntry, user_input: dict[str, Any]) -> Any:
    result = await _start_flow(hass, entry)
    assert result["type"] is FlowResultType.FORM
    return await hass.config_entries.subentries.async_configure(result["flow_id"], user_input)


async def _summaries(hass: HomeAssistant, entity_id: str) -> list[str]:
    response = await hass.services.async_call(
        "calendar",
        "get_events",
        {"entity_id": entity_id, "start_date_time": DAY_START, "duration": {"hours": 24}},
        blocking=True,
        return_response=True,
    )
    return [event["summary"] for event in response[entity_id]["events"]]


async def test_include_calendar_via_form_end_to_end(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
    forbid_loop_io: None,
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(MOTORSPORT_FEED, calendars=())

    result = await _start_flow(hass, entry)
    assert result["type"] is FlowResultType.FORM
    assert {"name", "channels", "channel_regex", "include", "exclude"} <= set(_schema_keys(result))
    hass.config_entries.subentries.async_abort(result["flow_id"])

    result = await complete_calendar_flow(hass, entry, {"name": "Formel 1", "include": r"formel\s*1|formula\s*1"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    # Every save stores the full key set (D-06)
    assert result["data"] == with_defaults(
        {"channels": [], "channel_regex": "", "include": r"formel\s*1|formula\s*1", "exclude": ""}
    )
    await hass.async_block_till_done()

    assert await _summaries(hass, "calendar.formel_1") == [
        "Das Erste: Formel 1: Rennen",
        "ZDF: Formula 1 Highlights",
    ]


@pytest.mark.parametrize(
    ("user_input", "expected"),
    [
        ({"exclude": "rennen"}, ["ZDF: Formula 1 Highlights"]),
        ({"channel_regex": "^zdf"}, ["ZDF: Formula 1 Highlights"]),
        (
            {"channels": ["daserste.de"], "channel_regex": "^zdf"},
            ["Das Erste: Formel 1: Rennen", "ZDF: Formula 1 Highlights"],
        ),
    ],
    ids=["exclude", "channel-regex", "channels-or-regex"],
)
async def test_form_filters_are_applied(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
    user_input: dict[str, Any],
    expected: list[str],
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(MOTORSPORT_FEED, calendars=())

    result = await complete_calendar_flow(
        hass, entry, {"name": "Motorsport", "include": r"formel\s*1|formula\s*1", **user_input}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    assert await _summaries(hass, "calendar.motorsport") == expected


# --- Validation (FLT-07), unloaded sources and the channel picker -----------------------------------------------


@pytest.mark.parametrize(
    ("user_input", "field", "pattern"),
    [
        ({"include": "ok\n("}, "include", "("),
        ({"exclude": "rennen\n[a-"}, "exclude", "[a-"),
        ({"channel_regex": "^zdf\n*sky"}, "channel_regex", "*sky"),
        ({"include": "ok\na{99999999999}"}, "include", "a{99999999999}"),
        ({"exclude": "a{1,99999999999}"}, "exclude", "a{1,99999999999}"),
        ({"channel_regex": "zdf{99999999999}"}, "channel_regex", "zdf{99999999999}"),
    ],
    ids=[
        "include",
        "exclude",
        "channel-regex",
        "include-repeat-overflow",
        "exclude-repeat-overflow",
        "channel-regex-repeat-overflow",
    ],
)
async def test_invalid_pattern_line_keeps_form_open(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    user_input: dict[str, str],
    field: str,
    pattern: str,
) -> None:
    entry = await setup_xmltv(MOTORSPORT_FEED, calendars=())

    result = await _submit(hass, entry, {"name": "Broken", **user_input})

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {field: "invalid_regex"}
    assert result["description_placeholders"]["pattern"] == pattern
    assert result["description_placeholders"]["error"]  # the regex message; its wording is not asserted
    assert not entry.subentries


async def test_nested_repetition_rejected_in_form(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(MOTORSPORT_FEED, calendars=())

    result = await _submit(hass, entry, {"name": "Slow", "include": "^(\\w+\\s?)+$"})

    # T-02-16: refused before it is stored, so it never runs over the feed
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"include": "invalid_regex"}
    assert result["description_placeholders"]["pattern"] == "^(\\w+\\s?)+$"
    assert "nested repetition" in result["description_placeholders"]["error"]
    assert not entry.subentries


@pytest.mark.parametrize(
    ("field", "text"),
    [
        ("exclude", "x" * 301),
        ("include", "ok\n" + "y" * 301),
        ("channel_regex", "\n".join(f"channel{index}" for index in range(51))),
        ("include", "\n\n".join(f"show{index}" for index in range(51))),
    ],
    ids=["exclude-301-chars", "include-301-chars", "channel-regex-51-lines", "include-51-lines-with-blanks"],
)
async def test_oversized_patterns_are_rejected(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    field: str,
    text: str,
) -> None:
    entry = await setup_xmltv(MOTORSPORT_FEED, calendars=())

    result = await _submit(hass, entry, {"name": "Too much", field: text})

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {field: "invalid_regex"}
    assert result["description_placeholders"]["error"]
    assert not entry.subentries


async def test_fifty_patterns_and_300_chars_are_accepted(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(MOTORSPORT_FEED, calendars=())
    include = "\n".join(["z" * 300, *(f"show{index}" for index in range(49))])

    result = await complete_calendar_flow(hass, entry, {"name": "At the limit", "include": include})

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_blank_lines_only_are_ignored(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(MOTORSPORT_FEED, calendars=())

    result = await complete_calendar_flow(
        hass, entry, {"name": "Das Erste", "channels": ["daserste.de"], "include": "\n\n", "exclude": "  \n"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    assert await _summaries(hass, "calendar.das_erste") == ["Das Erste: Formel 1: Rennen", "Das Erste: Tagesschau"]


async def test_input_is_kept_after_a_validation_error(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(MOTORSPORT_FEED, calendars=())
    user_input = {
        "name": "Formel 1",
        "channels": ["zdf.de"],
        "channel_regex": "^daserste",
        "include": "formel\\s*1\n(",
        "exclude": "highlights",
    }

    result = await _submit(hass, entry, user_input)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"include": "invalid_regex"}
    for name, value in user_input.items():
        assert _schema_key(result, name).description["suggested_value"] == value

    # The user fixes the line and submits again in the same flow, then saves from the preview
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {**user_input, "include": "formel\\s*1"}
    )
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {"next_step_id": "save"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["include"] == "formel\\s*1"


async def test_blank_name_is_rejected(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(MOTORSPORT_FEED, calendars=())

    result = await _submit(hass, entry, {"name": "   "})

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"name": "name_required"}


async def test_unloaded_source_aborts(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(FEED_URL, status=500)
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Broken EPG",
        data={"source_type": "url", "url": FEED_URL},
        options={"refresh_hours": 24},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY

    result = await _start_flow(hass, entry)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "source_not_loaded"


async def test_channel_picker_lists_sorted_ids(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    channels = """
      <channel id="zdf.de"><display-name>ZDF</display-name></channel>
      <channel id="arte.de"><display-name>arte</display-name></channel>
      <channel id="daserste.de"><display-name>Das Erste</display-name></channel>
    """
    entry = await setup_xmltv(_feed("", channels=channels), calendars=())

    result = await _start_flow(hass, entry)

    options = result["data_schema"].schema[_schema_key(result, "channels")].config["options"]
    assert list(options) == ["arte.de", "daserste.de", "zdf.de"]
    assert all(isinstance(option, str) for option in options)  # IDs only, no display-name labels (D-03)


async def test_channel_selection_order_does_not_change_matches(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(MOTORSPORT_FEED, calendars=())

    for name, channels in (("Forward", ["daserste.de", "zdf.de"]), ("Reverse", ["zdf.de", "daserste.de"])):
        result = await complete_calendar_flow(hass, entry, {"name": name, "channels": channels})
        assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    forward = await _summaries(hass, "calendar.forward")
    assert len(forward) == 4
    assert await _summaries(hass, "calendar.reverse") == forward


# --- Preview step (FLT-10, D-01, D-15, D-18) ---------------------------------------------------------------------


async def test_back_returns_prefilled_form(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(MOTORSPORT_FEED, calendars=())
    user_input = {
        "name": "Motorsport",
        "channels": ["zdf.de"],
        "channel_regex": "^das",
        "include": "formula",  # matches the ZDF highlights, so the preview is not empty
        "exclude": "rennen",
    }

    result = await _submit(hass, entry, user_input)
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {"next_step_id": "back"})

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "basic"
    for name, value in user_input.items():
        assert _schema_key(result, name).description["suggested_value"] == value

    result = await hass.config_entries.subentries.async_configure(result["flow_id"], user_input)
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "preview"
    assert not entry.subentries


async def test_empty_preview_still_saves(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(MOTORSPORT_FEED, calendars=())

    result = await _submit(hass, entry, {"name": "Nothing", "include": "no-such-show"})
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "preview_empty"
    assert list(result["menu_options"]) == ["save", "back"]

    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {"next_step_id": "save"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    assert hass.states.get("calendar.nothing") is not None
    assert await _summaries(hass, "calendar.nothing") == []


async def test_save_on_unloaded_source_aborts(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(MOTORSPORT_FEED, calendars=())

    result = await _submit(hass, entry, {"name": "Late"})
    assert result["type"] is FlowResultType.MENU
    entry.mock_state(hass, ConfigEntryState.SETUP_RETRY)
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {"next_step_id": "save"})

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "source_not_loaded"
    assert not entry.subentries


@pytest.mark.parametrize(
    "user_input",
    [
        {"name": "All"},
        {"name": "Formel 1", "include": "formel"},
        {"name": "Nothing", "include": "no-such-show"},
        {"name": "ZDF", "channels": ["zdf.de"], "exclude": "heute"},
    ],
    ids=["all", "include", "no-match", "channel-exclude"],
)
async def test_form_submit_never_creates_directly(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
    user_input: dict[str, Any],
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(MOTORSPORT_FEED, calendars=())

    result = await _submit(hass, entry, user_input)

    assert result["type"] is FlowResultType.MENU
    assert not entry.subentries
