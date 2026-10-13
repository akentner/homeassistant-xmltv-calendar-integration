"""Calendar subentry flow: the "Add calendar" form, its filters and their validation."""

from typing import TYPE_CHECKING, Any

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry

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

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"name": "Formel 1", "include": r"formel\s*1|formula\s*1"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        "channels": [],
        "channel_regex": "",
        "include": r"formel\s*1|formula\s*1",
        "exclude": "",
    }
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

    result = await _submit(hass, entry, {"name": "Motorsport", "include": r"formel\s*1|formula\s*1", **user_input})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    assert await _summaries(hass, "calendar.motorsport") == expected
