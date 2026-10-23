"""Production-path regressions for matching independently of entity admission."""

from typing import TYPE_CHECKING, Any

from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import async_capture_events, async_fire_time_changed

from .test_new_match_event import EVENT, NOW, _refresh, _reload, _stored_seen
from .test_retention import RACE_MARKER, RACE_SUMMARY, _retained_titles, _stored, _summaries, _variant
from .test_sensor import BASIC_FEED, F1, RACE, SENSOR

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    import pytest
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker


async def test_disabled_calendar_keeps_matching(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    aioclient_mock: AiohttpClientMocker,
    hass_storage: dict[str, Any],
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    freezer.move_to(NOW)
    events = async_capture_events(hass, EVENT)
    entry = await setup_xmltv(BASIC_FEED, calendars=F1)
    registry = er.async_get(hass)
    registry.async_update_entity("calendar.f1", disabled_by=er.RegistryEntryDisabler.USER)
    await _reload(hass, entry)

    assert hass.states.get("calendar.f1") is None
    assert hass.states.get(SENSOR).state == "2026-10-13T10:00:00+00:00"
    assert events == []

    await _refresh(hass, aioclient_mock, entry, BASIC_FEED.replace(b"</tv>", RACE))
    state = hass.states.get(SENSOR)
    assert state.state == "2026-10-13T07:00:00+00:00"
    assert state.attributes["summary"] == "Das Erste: Formel 1: Rennen"
    seen = await _stored_seen(hass_storage, entry)
    (uid,) = [key for key in seen if key.startswith("daserste.de-20261013T070000Z-")]
    assert seen[uid] == 1791882000
    assert [event.data for event in events] == [
        {
            "entity_id": "calendar.f1",
            "calendar": "F1",
            "title": "Formel 1: Rennen",
            "summary": "Das Erste: Formel 1: Rennen",
            "channel": "Das Erste",
            "channel_id": "daserste.de",
            "start": "2026-10-13T09:00:00+02:00",
            "end": "2026-10-13T11:00:00+02:00",
            "uid": uid,
        }
    ]


async def test_disabled_counts_without_calendar_objects(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    monkeypatch: pytest.MonkeyPatch,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    from custom_components.xmltv_calendar.diagnostics import async_get_config_entry_diagnostics
    from custom_components.xmltv_calendar.sensor import LastFetchSensor

    monkeypatch.setattr(LastFetchSensor, "_attr_entity_registry_enabled_default", True)
    freezer.move_to(NOW)
    entry = await setup_xmltv(BASIC_FEED, calendars=(*F1, ("ZDF", {"channels": ["zdf.de"]})))
    registry = er.async_get(hass)
    registry.async_update_entity("calendar.f1", disabled_by=er.RegistryEntryDisabler.USER)
    await _reload(hass, entry)
    # HA never admits this presentation; consumers must not need even a constructed calendar facade.
    sid = next(sid for sid, sub in entry.subentries.items() if sub.title == "F1")
    entry.runtime_data.calendars.pop(sid)
    await _refresh(hass, aioclient_mock, entry, BASIC_FEED.replace(b"</tv>", RACE))

    assert hass.states.get("sensor.f1_last_fetch").attributes["matches"] == 3
    assert hass.states.get("sensor.zdf_last_fetch").attributes["matches"] == 2
    assert (await async_get_config_entry_diagnostics(hass, entry))["calendars"] == [
        {"title": "F1", "matches": 3, "retained": 0},
        {"title": "ZDF", "matches": 2, "retained": 0},
    ]
    assert hass.states.get(SENSOR).state == "2026-10-13T07:00:00+00:00"
    calls = aioclient_mock.call_count
    freezer.move_to("2026-10-13T07:00:00+00:00")
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(SENSOR).state == "2026-10-13T10:00:00+00:00"
    assert aioclient_mock.call_count == calls


async def test_disabled_edits_and_retained_reenable(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    aioclient_mock: AiohttpClientMocker,
    hass_storage: dict[str, Any],
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    from custom_components.xmltv_calendar.diagnostics import async_get_config_entry_diagnostics

    freezer.move_to(NOW)
    entry = await setup_xmltv(_variant(0), calendars=F1)
    registry = er.async_get(hass)
    for entity_id in ("calendar.f1", SENSOR):
        registry.async_update_entity(entity_id, disabled_by=er.RegistryEntryDisabler.USER)
    await _reload(hass, entry)
    (sid,) = entry.subentries
    freezer.move_to("2026-10-13T12:00:00+00:00")
    await _refresh(hass, aioclient_mock, entry, _variant(1, BASIC_FEED, RACE_MARKER))
    assert _retained_titles(await _stored(hass_storage, entry)) == ["Formel 1: Großer Preis von Mexiko"]
    assert (await async_get_config_entry_diagnostics(hass, entry))["calendars"] == [
        {"title": "F1", "matches": 1, "retained": 1}
    ]
    calls = aioclient_mock.call_count
    assert hass.config_entries.async_update_subentry(
        entry,
        entry.subentries[sid],
        data={"channels": ["daserste.de"], "title_template": "{title}", "retention_days": 3},
    )
    await hass.async_block_till_done()
    assert aioclient_mock.call_count == calls
    await _reload(hass, entry)
    assert _retained_titles(await _stored(hass_storage, entry)) == ["Formel 1: Großer Preis von Mexiko"]
    for entity_id in ("calendar.f1", SENSOR):
        registry.async_update_entity(entity_id, disabled_by=None)
    await _reload(hass, entry)
    summaries = await _summaries(hass)
    assert "Formel 1: Großer Preis von Mexiko" in summaries
    assert RACE_SUMMARY not in summaries

    # Filter edits and template edits still reach the sensor with the calendar disabled.
    registry.async_update_entity("calendar.f1", disabled_by=er.RegistryEntryDisabler.USER)
    await _reload(hass, entry)
    assert hass.config_entries.async_update_subentry(
        entry,
        entry.subentries[sid],
        data={"channels": ["zdf.de"], "title_template": "{title}"},
    )
    await hass.async_block_till_done()
    assert hass.states.get(SENSOR).attributes["summary"] == "heute"
    assert (await _stored(hass_storage, entry))["retained"] == []
    assert hass.config_entries.async_update_subentry(entry, entry.subentries[sid], data={"channels": ["absent"]})
    await hass.async_block_till_done()
    assert hass.states.get(SENSOR).state == "unknown"
