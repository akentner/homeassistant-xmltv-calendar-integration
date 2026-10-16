"""Several calendars per source: shared download, live add/remove, rename without refetch (FLT-01)."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .conftest import DOMAIN, complete_calendar_flow

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()
NOW = "2026-10-13T06:00:00+00:00"
pytestmark = pytest.mark.freeze_time(NOW)


def _subentry_id(entry: MockConfigEntry, title: str) -> str:
    (subentry_id,) = [sid for sid, sub in entry.subentries.items() if sub.title == title]
    return subentry_id


async def _summaries(hass: HomeAssistant, entity_id: str) -> list[str]:
    response = await hass.services.async_call(
        "calendar",
        "get_events",
        {"entity_id": entity_id, "start_date_time": "2026-10-13T00:00:00+00:00", "duration": {"hours": 24}},
        blocking=True,
        return_response=True,
    )
    return [event["summary"] for event in response[entity_id]["events"]]


async def test_two_calendars_one_download(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    await setup_xmltv(FEED, calendars=(("A", {}), ("B", {"channels": ["zdf.de"]})))

    assert hass.states.get("calendar.a") is not None
    assert hass.states.get("calendar.b") is not None
    assert aioclient_mock.call_count == 1


async def test_add_calendar_via_flow_no_refetch(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(FEED, calendars=(("A", {}), ("B", {"channels": ["zdf.de"]})))
    calls = aioclient_mock.call_count

    result = await complete_calendar_flow(hass, entry, {"name": "C", "channels": ["daserste.de"]})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    assert hass.states.get("calendar.c") is not None
    assert await _summaries(hass, "calendar.c") == [
        "Das Erste: Formel 1: Großer Preis von Mexiko",
        "Das Erste: Tagesschau",
    ]
    assert aioclient_mock.call_count == calls
    assert set(entry.runtime_data.calendars) == set(entry.subentries)


async def test_remove_calendar_removes_entity_and_device(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(FEED, calendars=(("A", {}), ("B", {"channels": ["zdf.de"]})))
    calls = aioclient_mock.call_count
    b_id = _subentry_id(entry, "B")
    device_registry = dr.async_get(hass)
    assert device_registry.async_get_device_by_identifier((DOMAIN, b_id), entry.entry_id) is not None
    a_events = await _summaries(hass, "calendar.a")
    runtime = entry.runtime_data

    assert hass.config_entries.async_remove_subentry(entry, b_id)
    await hass.async_block_till_done()

    assert hass.states.get("calendar.b") is None
    assert device_registry.async_get_device_by_identifier((DOMAIN, b_id), entry.entry_id) is None
    assert entry.runtime_data is runtime
    assert b_id not in runtime.calendars
    assert await _summaries(hass, "calendar.a") == a_events
    assert len(a_events) == 4
    assert aioclient_mock.call_count == calls


async def test_rename_source_does_not_reload(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED, calendars=(("A", {}),))
    calls = aioclient_mock.call_count
    runtime = entry.runtime_data

    hass.config_entries.async_update_entry(entry, title="Renamed")
    await hass.async_block_till_done()

    assert entry.title == "Renamed"
    assert entry.runtime_data is runtime
    assert entry.state is ConfigEntryState.LOADED
    assert aioclient_mock.call_count == calls


async def test_options_change_reloads_once(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(FEED, calendars=(("A", {}), ("B", {})))
    calls = aioclient_mock.call_count
    runtime = entry.runtime_data

    hass.config_entries.async_update_entry(entry, options={"refresh_hours": 12})
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data is not runtime
    # The reload re-parses the disk cache, which is still fresh for the new 12 h interval: no download (D-08, D-16)
    assert aioclient_mock.call_count == calls
    assert entry.runtime_data.coordinator.next_refresh_at == datetime.fromisoformat(NOW) + timedelta(hours=12)
    assert hass.states.get("calendar.a") is not None
    assert hass.states.get("calendar.b") is not None


async def test_data_change_reloads_once(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED, calendars=(("A", {}),))
    other_url = "https://epg.example.com/other.xml"
    aioclient_mock.get(other_url, content=FEED)
    calls = aioclient_mock.call_count

    hass.config_entries.async_update_entry(entry, data={"source_type": "url", "url": other_url})
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert aioclient_mock.call_count == calls + 1
    assert aioclient_mock.mock_calls[-1][1].human_repr() == other_url


async def test_preexisting_subentries_get_one_entity_each(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED, calendars=(("A", {}), ("B", {"channels": ["zdf.de"]}), ("C", {})))

    entities = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    assert len(entities) == len(entry.subentries) == 3
    assert sorted(entity.unique_id for entity in entities) == sorted(entry.subentries)
    assert len(entry.runtime_data.calendars) == 3

    device_registry = dr.async_get(hass)
    for subentry_id in entry.subentries:
        device = device_registry.async_get_device_by_identifier((DOMAIN, subentry_id), entry.entry_id)
        assert device is not None
        assert device.config_subentry_id == subentry_id
    for entity in entities:
        assert entity.config_subentry_id == entity.unique_id


async def test_identical_filters_make_two_entities(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(FEED, calendars=(("Same", {}), ("Same", {})))

    assert hass.states.get("calendar.same") is not None
    assert hass.states.get("calendar.same_2") is not None
    assert len(entry.runtime_data.calendars) == 2
    assert await _summaries(hass, "calendar.same") == await _summaries(hass, "calendar.same_2")


async def test_zero_calendars_loads(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED, calendars=())

    assert entry.state is ConfigEntryState.LOADED
    assert hass.states.async_entity_ids("calendar") == []
    assert er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id) == []


async def test_add_and_remove_order_does_not_change_events(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    freezer: Any,
) -> None:
    freezer.move_to(NOW)
    entry = await setup_xmltv(
        FEED, calendars=(("ZDF", {"channels": ["zdf.de"]}), ("Erste", {"channels": ["daserste.de"]}))
    )
    zdf = await _summaries(hass, "calendar.zdf")
    erste = await _summaries(hass, "calendar.erste")

    # Remove the first-added calendar and add a third one; the remaining calendar is unaffected
    assert hass.config_entries.async_remove_subentry(entry, _subentry_id(entry, "ZDF"))
    await hass.async_block_till_done()
    result = await complete_calendar_flow(hass, entry, {"name": "ZDF again", "channels": ["zdf.de"]})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    assert await _summaries(hass, "calendar.erste") == erste
    assert await _summaries(hass, "calendar.zdf_again") == zdf
