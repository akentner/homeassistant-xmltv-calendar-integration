"""The shipped automation blueprint: notify before a matching programme starts (AUT-05)."""

import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import async_fire_time_changed, async_mock_service

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant, ServiceCall

ROOT = Path(__file__).parent.parent
BLUEPRINT = ROOT / "blueprints" / "automation" / "xmltv_calendar" / "notify_before_programme.yaml"
BLUEPRINT_PATH = "xmltv_calendar/notify_before_programme.yaml"
BASIC_FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()


def _install_blueprint(hass: HomeAssistant) -> None:
    """Copy the shipped blueprint into the test config dir, where use_blueprint looks for it."""
    assert BLUEPRINT.is_file(), f"blueprint missing: {BLUEPRINT.relative_to(ROOT)}"
    target = Path(hass.config.path("blueprints/automation/xmltv_calendar"))
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy(BLUEPRINT, target)


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
    assert {data["title"] for _, data in fired} == {"Das Erste: Formel 1: Großer Preis von Mexiko", "ZDF: heute"}
    for _, data in fired:
        assert data["entity_id"] == ["notify.phone"]
        assert "12:00" in data["message"]
