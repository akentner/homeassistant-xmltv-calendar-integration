"""Diagnostics of a source entry: structure, state and counts, never feed content or secrets (SRC-12, D-21)."""

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from pytest_homeassistant_custom_component.components.diagnostics import get_diagnostics_for_config_entry

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()
NOW = "2026-10-13T06:00:00+00:00"
# Fake credentials, token and validator the diagnostics must never show
SECRET_URL = "https://user:hunter2@epg.example.com/guide.xml?token=s3cret"  # noqa: S105
FEED_ETAG = '"v1-secret-etag"'
pytestmark = pytest.mark.freeze_time(NOW)


async def test_diagnostics_end_to_end(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(
        FEED,
        calendars=(("B", {"channels": ["zdf.de"]}), ("A", {})),
        url=SECRET_URL,
        headers={"ETag": FEED_ETAG},
    )

    result = await get_diagnostics_for_config_entry(hass, hass_client, entry)

    assert result["source"] == {"source_type": "url", "url": "https://epg.example.com/**REDACTED**"}
    assert result["options"] == {
        "refresh_mode": "interval",
        "refresh_hours": 24,
        "naive_timezone": "utc",
        "offset_minutes": 0,
    }
    assert result["health"] == {
        "last_success": NOW,
        "failing_since": None,
        "last_failure": None,
        "consecutive_failures": 0,
    }
    assert result["cache"] == {"fetched_at": NOW, "size": len(FEED), "has_etag": True, "has_last_modified": False}
    assert result["stats"] == {
        "programmes": 4,
        "channels": 2,
        "skipped_malformed": 0,
        "duplicates": 0,
        "inferred_stops": 0,
        "dropped_past": 0,
    }
    assert result["calendars"] == [{"title": "A", "matches": 4}, {"title": "B", "matches": 2}]
    assert result["next_refresh"] == "2026-10-14T06:00:00+00:00"
    dumped = json.dumps(result)
    for secret in ("hunter2", "user:", "s3cret", "guide.xml", "v1-secret-etag", "Tagesschau"):
        assert secret not in dumped
