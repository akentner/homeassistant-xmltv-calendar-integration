"""The shipped automation blueprint: notify before a matching programme starts (AUT-05)."""

import logging
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

from homeassistant.components.automation.config import AUTOMATION_BLUEPRINT_SCHEMA
from homeassistant.components.blueprint.models import Blueprint
from homeassistant.setup import async_setup_component
from homeassistant.util.yaml import load_yaml
from pytest_homeassistant_custom_component.common import async_fire_time_changed, async_mock_service

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    import pytest
    from homeassistant.core import HomeAssistant, ServiceCall

ROOT = Path(__file__).parent.parent
BLUEPRINT = ROOT / "blueprints" / "automation" / "xmltv_calendar" / "notify_before_programme.yaml"
BLUEPRINT_PATH = "xmltv_calendar/notify_before_programme.yaml"
BASIC_FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()
# Formel 1 (Das Erste) and heute (ZDF) both start 10:00 UTC (12:00 Berlin)
PROGRAMME_START = datetime(2026, 10, 13, 10, 0, tzinfo=UTC)
BOTH_TITLES = {"Das Erste: Formel 1: Großer Preis von Mexiko", "ZDF: heute"}


def _install_blueprint(hass: HomeAssistant) -> None:
    """Copy the shipped blueprint into the test config dir, where use_blueprint looks for it."""
    assert BLUEPRINT.is_file(), f"blueprint missing: {BLUEPRINT.relative_to(ROOT)}"
    target = Path(hass.config.path("blueprints/automation/xmltv_calendar"))
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy(BLUEPRINT, target)


def _raw_blueprint() -> dict[str, Any]:
    return load_yaml(BLUEPRINT)  # type: ignore[return-value]


async def _setup_automation(hass: HomeAssistant, inputs: dict[str, Any]) -> None:
    assert await async_setup_component(
        hass,
        "automation",
        {"automation": {"use_blueprint": {"path": BLUEPRINT_PATH, "input": inputs}}},
    )
    await hass.async_block_till_done()


async def _run_until(
    hass: HomeAssistant, freezer: Any, calls: list[ServiceCall], start: datetime, end: datetime
) -> list[tuple[datetime, dict[str, Any]]]:
    """Step one minute at a time (coarse jumps skip trigger windows); return (minute, data) per call."""
    fired: list[tuple[datetime, dict[str, Any]]] = []
    now = start
    while now < end:
        now += timedelta(minutes=1)
        freezer.move_to(now.isoformat())
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
        fired.extend((now, dict(call.data)) for call in calls[len(fired) :])
    # Stop the automations so the calendar trigger's refresh timer does not linger past the test
    await hass.services.async_call("automation", "turn_off", {"entity_id": "all"}, blocking=True)
    return fired


async def test_overlapping_programmes_notify_once_each(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    # Formel 1 (Das Erste) and heute (ZDF) both start 10:00 UTC (12:00 Berlin); 09:30 is a 15-minute boundary
    start = datetime(2026, 10, 13, 9, 30, tzinfo=UTC)
    freezer.move_to(start.isoformat())
    await setup_xmltv(BASIC_FEED, calendars=(("Test", {}),))
    _install_blueprint(hass)
    notify = async_mock_service(hass, "notify", "send_message")
    await _setup_automation(hass, {"calendar_entity": "calendar.test", "notify_entity": ["notify.phone"]})

    fired = await _run_until(hass, freezer, notify, start, datetime(2026, 10, 13, 10, 5, tzinfo=UTC))

    assert len(fired) == 2
    assert {at for at, _ in fired} == {datetime(2026, 10, 13, 9, 50, tzinfo=UTC)}
    assert {data["title"] for _, data in fired} == BOTH_TITLES
    for _, data in fired:
        assert data["entity_id"] == ["notify.phone"]
        assert "12:00" in data["message"]


def test_blueprint_passes_home_assistant_schema() -> None:
    blueprint = Blueprint(_raw_blueprint(), expected_domain="automation", schema=AUTOMATION_BLUEPRINT_SCHEMA)

    assert set(blueprint.inputs) == {"calendar_entity", "lead_time", "notify_entity", "actions"}
    assert blueprint.metadata["homeassistant"]["min_version"] == "2026.3.0"
    assert blueprint.metadata["source_url"].endswith(
        "/blob/main/blueprints/automation/xmltv_calendar/notify_before_programme.yaml"
    )


def test_blueprint_contract() -> None:
    raw = _raw_blueprint()
    inputs = raw["blueprint"]["input"]

    assert raw["mode"] == "queued"
    assert len(raw["triggers"]) == 1
    assert raw["triggers"][0]["trigger"] == "calendar"
    assert raw["triggers"][0]["event"] == "start"
    assert inputs["calendar_entity"]["selector"]["entity"]["filter"] == [
        {"integration": "xmltv_calendar", "domain": "calendar"}
    ]
    assert inputs["lead_time"]["selector"]["duration"]["allow_negative"] is True
    assert inputs["lead_time"]["default"] == {"hours": 0, "minutes": -10, "seconds": 0}


async def test_custom_actions_get_programme_variables(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    start = datetime(2026, 10, 13, 9, 45, tzinfo=UTC)
    freezer.move_to(start.isoformat())
    await setup_xmltv(BASIC_FEED, calendars=(("Test", {}),))
    _install_blueprint(hass)
    calls = async_mock_service(hass, "test", "automation")
    await _setup_automation(
        hass,
        {
            "calendar_entity": "calendar.test",
            "lead_time": {"hours": 0, "minutes": -5, "seconds": 0},
            "actions": [
                {
                    "action": "test.automation",
                    "data": {
                        "title": "{{ title }}",
                        "channel": "{{ channel }}",
                        "start": "{{ start }}",
                        "end": "{{ end }}",
                        "start_time": "{{ start_time }}",
                    },
                }
            ],
        },
    )

    fired = await _run_until(hass, freezer, calls, start, PROGRAMME_START + timedelta(minutes=5))

    assert len(fired) == 2
    assert {at for at, _ in fired} == {datetime(2026, 10, 13, 9, 55, tzinfo=UTC)}
    assert {data["title"] for _, data in fired} == BOTH_TITLES
    formel1 = next(data for _, data in fired if "Formel 1" in data["title"])
    assert formel1["channel"] == "Das Erste"
    assert formel1["start_time"] == "12:00"
    assert datetime.fromisoformat(str(formel1["start"])) == PROGRAMME_START
    assert datetime.fromisoformat(str(formel1["end"])) == datetime(2026, 10, 13, 11, 30, tzinfo=UTC)


async def test_default_action_without_notify_entity_does_nothing(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    setup_xmltv: Callable[..., Awaitable[Any]],
    caplog: pytest.LogCaptureFixture,
) -> None:
    start = datetime(2026, 10, 13, 9, 45, tzinfo=UTC)
    freezer.move_to(start.isoformat())
    await setup_xmltv(BASIC_FEED, calendars=(("Test", {}),))
    _install_blueprint(hass)
    notify = async_mock_service(hass, "notify", "send_message")
    await _setup_automation(hass, {"calendar_entity": "calendar.test"})

    with caplog.at_level(logging.WARNING):
        fired = await _run_until(hass, freezer, notify, start, PROGRAMME_START + timedelta(minutes=5))

    assert fired == []
    # The automation did run (so the guard, not a missing trigger, kept it quiet) and logged no error
    automations = hass.states.async_all("automation")
    assert len(automations) == 1
    assert automations[0].attributes["last_triggered"] is not None
    assert not [
        record
        for record in caplog.records
        if record.name.startswith("homeassistant.components.automation") and record.levelno >= logging.ERROR
    ]


async def test_lead_time_zero_fires_at_start(
    hass: HomeAssistant,
    freezer: Any,
    berlin_tz: None,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    # Start off the 15-minute grid: 10:00 then lies inside the first trigger window. On a window boundary the
    # refresh schedules the already-due alarm, which the minute stepping only runs on the next tick (10:01)
    start = datetime(2026, 10, 13, 9, 50, tzinfo=UTC)
    freezer.move_to(start.isoformat())
    await setup_xmltv(BASIC_FEED, calendars=(("Test", {}),))
    _install_blueprint(hass)
    notify = async_mock_service(hass, "notify", "send_message")
    await _setup_automation(
        hass,
        {
            "calendar_entity": "calendar.test",
            "lead_time": {"hours": 0, "minutes": 0, "seconds": 0},
            "notify_entity": ["notify.phone"],
        },
    )

    fired = await _run_until(hass, freezer, notify, start, PROGRAMME_START + timedelta(minutes=5))

    assert len(fired) == 2
    assert {at for at, _ in fired} == {PROGRAMME_START}
    assert {data["title"] for _, data in fired} == BOTH_TITLES
