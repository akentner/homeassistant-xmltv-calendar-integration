"""Last-fetch diagnostic sensor: the source's last refresh run on every calendar device (AUT-06, D-20..D-24)."""

import importlib
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from homeassistant.const import EntityCategory
from homeassistant.helpers import entity_registry as er

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry

FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()
NOW = "2026-10-13T06:00:00+00:00"
SENSOR = "sensor.test_last_fetch"
pytestmark = pytest.mark.freeze_time(NOW)


@pytest.fixture
def last_fetch_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enable the disabled-by-default sensor; phcc has no entity_registry_enabled_by_default fixture (Pitfall 7)."""
    sensor = importlib.import_module("custom_components.xmltv_calendar.sensor")
    last_fetch = getattr(sensor, "LastFetchSensor", None)
    if last_fetch is not None:
        monkeypatch.setattr(last_fetch, "_attr_entity_registry_enabled_default", True)


@pytest.mark.usefixtures("last_fetch_enabled")
async def test_download_shows_last_fetch(
    hass: HomeAssistant, setup_xmltv: Callable[..., Awaitable[MockConfigEntry]]
) -> None:
    await setup_xmltv(FEED, calendars=(("Test", {}),))

    state = hass.states.get(SENSOR)
    assert state is not None
    assert state.state == NOW
    attributes = state.attributes
    expected = {
        "trigger": "startup",
        "outcome": "downloaded",
        "http_status": 200,
        "failure_reason": None,
        "cache": "written",
        "sent_etag": False,
        "sent_last_modified": False,
        "bytes": len(FEED),
        "programmes": 4,
        "channels": 2,
        "matches": 4,
        "consecutive_failures": 0,
    }
    assert {key: attributes.get(key, "missing") for key in expected} == expected
    assert isinstance(attributes["parse_duration"], float)
    assert attributes["parse_duration"] >= 0
    assert isinstance(attributes["last_success"], str)
    assert isinstance(attributes["next_refresh"], str)


async def test_last_fetch_is_diagnostic_and_disabled_by_default(
    hass: HomeAssistant, setup_xmltv: Callable[..., Awaitable[MockConfigEntry]]
) -> None:
    entry = await setup_xmltv(FEED, calendars=(("Test", {}),))
    (subentry_id,) = entry.subentries

    registry = er.async_get(hass)
    sensor = registry.async_get(SENSOR)
    calendar = registry.async_get("calendar.test")
    assert sensor is not None
    assert calendar is not None
    assert sensor.entity_category is EntityCategory.DIAGNOSTIC
    assert sensor.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert sensor.unique_id == f"{subentry_id}_last_fetch"
    assert sensor.device_id == calendar.device_id
    assert hass.states.get(SENSOR) is None
