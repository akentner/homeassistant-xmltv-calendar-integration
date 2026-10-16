"""Per-source timezone options end to end: offset-less timestamps as local time, offset correction (SRC-10)."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

import pytest
from homeassistant.components.calendar.const import DATA_COMPONENT
from homeassistant.config_entries import ConfigEntryState, ConfigSubentryData
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.xmltv_calendar.const import (
    CONF_NAIVE_TIMEZONE,
    CONF_OFFSET_MINUTES,
    CONF_REFRESH_HOURS,
    DOMAIN,
    NAIVE_TZ_LOCAL,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from pathlib import Path

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

NOW = "2026-10-13T06:00:00+00:00"  # 08:00 in Europe/Berlin
pytestmark = [pytest.mark.freeze_time(NOW), pytest.mark.usefixtures("berlin_tz")]

NAIVE_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<tv>
  <channel id="daserste.de"><display-name>Das Erste</display-name></channel>
  <programme channel="daserste.de" start="20261013200000" stop="20261013201500"><title>Tagesschau</title></programme>
</tv>
"""

OFFSET_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<tv>
  <channel id="daserste.de"><display-name>Das Erste</display-name></channel>
  <programme channel="daserste.de" start="20261013200000 +0200" stop="20261013201500 +0200">
    <title>Tagesschau</title>
  </programme>
  <programme channel="daserste.de" start="20261013201500 +0200"><title>Wetter</title></programme>
  <programme channel="daserste.de" start="20261013203000 +0200" stop="20261013220000 +0200">
    <title>Krimi</title>
  </programme>
</tv>
"""


async def _events(hass: HomeAssistant) -> list[dict[str, Any]]:
    response = await hass.services.async_call(
        "calendar",
        "get_events",
        {"entity_id": "calendar.test", "start_date_time": "2026-10-13T00:00:00+02:00", "duration": {"hours": 24}},
        blocking=True,
        return_response=True,
    )
    return response["calendar.test"]["events"]


async def _starts(hass: HomeAssistant) -> list[str]:
    return [event["start"] for event in await _events(hass)]


async def _uids(hass: HomeAssistant) -> list[str | None]:
    entity = hass.data[DATA_COMPONENT].get_entity("calendar.test")
    assert entity is not None
    events = await entity.async_get_events(
        hass, datetime.fromisoformat("2026-10-13T00:00:00+02:00"), datetime.fromisoformat("2026-10-14T00:00:00+02:00")
    )
    return [event.uid for event in events]


async def _set_options(hass: HomeAssistant, entry: MockConfigEntry, **changes: Any) -> None:
    hass.config_entries.async_update_entry(entry, options={**entry.options, **changes})
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED


async def test_naive_local_timestamps_end_to_end(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    await setup_xmltv(NAIVE_FEED, options={CONF_REFRESH_HOURS: 24, CONF_NAIVE_TIMEZONE: NAIVE_TZ_LOCAL})

    events = await _events(hass)
    assert [(event["start"], event["end"]) for event in events] == [
        ("2026-10-13T20:00:00+02:00", "2026-10-13T20:15:00+02:00")
    ]


async def test_naive_timestamps_stay_utc_by_default(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    await setup_xmltv(NAIVE_FEED)

    events = await _events(hass)
    assert [(event["start"], event["end"]) for event in events] == [
        ("2026-10-13T22:00:00+02:00", "2026-10-13T22:15:00+02:00")
    ]


async def test_offset_correction_shifts_events(
    hass: HomeAssistant,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    await setup_xmltv(OFFSET_FEED, options={CONF_REFRESH_HOURS: 24, CONF_OFFSET_MINUTES: -60})

    events = await _events(hass)
    assert [(event["summary"], event["start"], event["end"]) for event in events] == [
        ("Das Erste: Tagesschau", "2026-10-13T19:00:00+02:00", "2026-10-13T19:15:00+02:00"),
        # The inferred stop follows the shifted start of the next programme
        ("Das Erste: Wetter", "2026-10-13T19:15:00+02:00", "2026-10-13T19:30:00+02:00"),
        ("Das Erste: Krimi", "2026-10-13T19:30:00+02:00", "2026-10-13T21:00:00+02:00"),
    ]


async def test_timezone_option_change_reparses_cache_without_download(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(NAIVE_FEED)
    runtime = entry.runtime_data
    assert aioclient_mock.call_count == 1
    assert await _starts(hass) == ["2026-10-13T22:00:00+02:00"]

    await _set_options(hass, entry, **{CONF_NAIVE_TIMEZONE: NAIVE_TZ_LOCAL})

    # D-16: the entry reloaded and re-parsed the fresh disk cache with the new option, no download
    assert entry.runtime_data is not runtime
    assert aioclient_mock.call_count == 1
    assert entry.runtime_data.coordinator.source_options.naive_timezone == NAIVE_TZ_LOCAL
    assert await _starts(hass) == ["2026-10-13T20:00:00+02:00"]


async def test_correction_change_changes_uids(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(OFFSET_FEED)
    unshifted = await _uids(hass)

    await _set_options(hass, entry, **{CONF_OFFSET_MINUTES: -60})
    shifted = await _uids(hass)
    starts = await _starts(hass)

    # Reloads with unchanged options re-parse the cache with the same correction once, never on top of the last one
    for _ in range(2):
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        assert await _uids(hass) == shifted
        assert await _starts(hass) == starts

    assert len(unshifted) == len(shifted) == 3
    assert set(unshifted).isdisjoint(shifted)  # accepted per D-16: the UTC start is part of the UID
    assert starts[0] == "2026-10-13T19:00:00+02:00"
    assert aioclient_mock.call_count == 1


@pytest.fixture
def feed_path(tmp_path: Path) -> Path:
    """Write the offset-less feed into a resolved temporary directory (is_allowed_path compares resolved paths)."""
    path = tmp_path.resolve() / "guide.xml"
    path.write_bytes(NAIVE_FEED)
    return path


async def test_file_source_uses_timezone_options(hass: HomeAssistant, feed_path: Path) -> None:
    path = feed_path
    hass.config.allowlist_external_dirs = {str(path.parent)}
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Local",
        data={"source_type": "file", "path": str(path)},
        options={CONF_REFRESH_HOURS: 24, CONF_NAIVE_TIMEZONE: NAIVE_TZ_LOCAL},
        subentries_data=[ConfigSubentryData(subentry_type="calendar", title="Test", data={}, unique_id=None)],
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    assert await _starts(hass) == ["2026-10-13T20:00:00+02:00"]

    await _set_options(hass, entry, **{CONF_OFFSET_MINUTES: 30})

    assert await _starts(hass) == ["2026-10-13T20:30:00+02:00"]
