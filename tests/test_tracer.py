"""End-to-end tracer: a URL source plus one calendar, created only through the flows."""

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import SOURCE_USER, ConfigEntryState
from homeassistant.data_entry_flow import FlowResultType

from .conftest import DOMAIN, FEED_URL

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

FIXTURE = Path(__file__).parent / "fixtures" / "basic.xml"


def _schema_key(result: Any, name: str) -> Any:
    """Return the voluptuous marker for `name` in a form result."""
    for key in result["data_schema"].schema:
        if key == name:
            return key
    msg = f"{name} not in form"
    raise AssertionError(msg)


async def test_url_source_to_calendar_events(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: Any,
    berlin_tz: None,
    forbid_loop_io: None,
) -> None:
    freezer.move_to("2026-10-13T10:30:00+00:00")
    aioclient_mock.get(FEED_URL, content=FIXTURE.read_bytes())

    # 1. Source flow: menu -> url
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.MENU
    assert "url" in result["menu_options"]
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "url"})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "url"

    # 2. url -> name (pre-filled with the host, D-09) -> entry
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"url": FEED_URL, "refresh_hours": 24})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "name"
    assert _schema_key(result, "name").description["suggested_value"] == "epg.example.com"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "Test EPG"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Test EPG"
    assert result["data"] == {"source_type": "url", "url": FEED_URL}
    assert result["options"] == {"refresh_hours": 24}
    await hass.async_block_till_done()
    entry = result["result"]
    assert entry.state is ConfigEntryState.LOADED

    # 3. Calendar subentry: channel picker from the loaded feed, no extra download
    calls_before = aioclient_mock.call_count
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "calendar"), context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    channels_selector = result["data_schema"].schema[_schema_key(result, "channels")]
    assert list(channels_selector.config["options"]) == ["daserste.de", "zdf.de"]
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"name": "Formel 1", "channels": ["daserste.de"]}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert aioclient_mock.call_count == calls_before

    # 4. Live state: the Formel 1 programme airs 10:00-11:30 UTC
    state = hass.states.get("calendar.formel_1")
    assert state is not None
    assert state.state == "on"
    assert state.attributes["location"] == "Das Erste"

    # 5. get_events returns only the selected channel's programmes
    response = await hass.services.async_call(
        "calendar",
        "get_events",
        {"entity_id": "calendar.formel_1", "start_date_time": "2026-10-13T00:00:00+00:00", "duration": {"hours": 24}},
        blocking=True,
        return_response=True,
    )
    events = response["calendar.formel_1"]["events"]
    assert [event["summary"] for event in events] == [
        "Das Erste: Formel 1: Großer Preis von Mexiko",
        "Das Erste: Tagesschau",
    ]
    for event in events:
        assert event["location"] == "Das Erste"
        assert datetime.fromisoformat(event["start"]).tzinfo is not None
        assert datetime.fromisoformat(event["end"]).tzinfo is not None
