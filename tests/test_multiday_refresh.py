"""Investigation: a 24 h URL source over several days with a feed that rolls forward every day."""

from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Any

from pytest_homeassistant_custom_component.common import async_fire_time_changed
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMockResponse
from yarl import URL

from .conftest import FEED_URL

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker


def _feed(first: date, days: int = 3) -> bytes:
    """Return a feed with one 'Formel 1 <date>' programme per day from `first` on, at 12:00 Berlin time."""
    programmes = "".join(
        f'<programme channel="daserste.de" start="{d:%Y%m%d}120000 +0200" stop="{d:%Y%m%d}133000 +0200">'
        f"<title>Formel 1 {d.isoformat()}</title></programme>"
        for d in (first + timedelta(days=i) for i in range(days))
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?><tv>'
        '<channel id="daserste.de"><display-name>Das Erste</display-name></channel>'
        f"{programmes}</tv>"
    ).encode()


class RollingServer:
    """A conditional-GET server whose feed version is set by the test; answers 304 for the current ETag."""

    def __init__(self, aioclient_mock: AiohttpClientMocker, first: date) -> None:
        """Serve the feed starting at `first`."""
        self._mock = aioclient_mock
        self.first = first

    @property
    def etag(self) -> str:
        return f'"{self.first.isoformat()}"'

    async def __call__(self, method: str, url: URL, data: Any) -> AiohttpClientMockResponse:
        headers = dict(self._mock.mock_calls[-1][3] or {})
        if headers.get("If-None-Match") == self.etag:
            return AiohttpClientMockResponse(method, URL(FEED_URL), status=304, headers={"ETag": self.etag})
        return AiohttpClientMockResponse(method, URL(FEED_URL), response=_feed(self.first), headers={"ETag": self.etag})


async def _summaries(hass: HomeAssistant, entity_id: str = "calendar.test") -> list[str]:
    response = await hass.services.async_call(
        "calendar",
        "get_events",
        {"entity_id": entity_id, "start_date_time": "2026-10-01T00:00:00+00:00", "duration": {"days": 40}},
        blocking=True,
        return_response=True,
    )
    return [event["summary"] for event in response[entity_id]["events"]]


async def _step_to(hass: HomeAssistant, freezer: Any, when: datetime) -> None:
    freezer.move_to(when)
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)


async def test_calendar_advances_every_day_without_reload(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    berlin_tz: None,
    freezer: Any,
) -> None:
    start = datetime.fromisoformat("2026-10-13T06:00:00+00:00")
    freezer.move_to(start)
    server = RollingServer(aioclient_mock, date(2026, 10, 13))
    aioclient_mock.get(FEED_URL, side_effect=server)
    entry = await setup_xmltv(b"", options={"refresh_hours": 24})
    coordinator = entry.runtime_data.coordinator
    assert "Das Erste: Formel 1 2026-10-15" in await _summaries(hass)

    for day in range(1, 5):
        # The provider publishes the next day a few hours before the refresh
        server.first = date(2026, 10, 13) + timedelta(days=day)
        newest = server.first + timedelta(days=2)
        await _step_to(hass, freezer, start + timedelta(days=day, seconds=1))
        summaries = await _summaries(hass)
        assert f"Das Erste: Formel 1 {newest.isoformat()}" in summaries, (day, summaries, coordinator.next_refresh_at)


async def test_calendar_advances_with_daily_reloads_in_between(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    berlin_tz: None,
    freezer: Any,
) -> None:
    """HA restarted (here: entry reloaded) at varying times every day; the disk cache serves the start."""
    start = datetime.fromisoformat("2026-10-13T06:00:00+00:00")
    freezer.move_to(start)
    server = RollingServer(aioclient_mock, date(2026, 10, 13))
    aioclient_mock.get(FEED_URL, side_effect=server)
    entry = await setup_xmltv(b"", options={"refresh_hours": 24})
    assert "Das Erste: Formel 1 2026-10-15" in await _summaries(hass)

    for day in range(1, 6):
        # Reload 14 h after the last regular refresh slot, with the cache still fresh
        await _step_to(hass, freezer, start + timedelta(days=day - 1, hours=14))
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done(wait_background_tasks=True)
        server.first = date(2026, 10, 13) + timedelta(days=day)
        newest = server.first + timedelta(days=2)
        await _step_to(hass, freezer, start + timedelta(days=day, seconds=1))
        summaries = await _summaries(hass)
        assert f"Das Erste: Formel 1 {newest.isoformat()}" in summaries, (
            day,
            summaries,
            entry.runtime_data.coordinator.next_refresh_at,
            aioclient_mock.call_count,
        )


async def test_calendar_advances_after_unchanged_days(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
    berlin_tz: None,
    freezer: Any,
) -> None:
    """Two refreshes answered 304, then the feed changes: the third refresh must reach the calendar."""
    start = datetime.fromisoformat("2026-10-13T06:00:00+00:00")
    freezer.move_to(start)
    server = RollingServer(aioclient_mock, date(2026, 10, 13))
    aioclient_mock.get(FEED_URL, side_effect=server)
    await setup_xmltv(b"", options={"refresh_hours": 24})
    await _step_to(hass, freezer, start + timedelta(days=1, seconds=1))
    await _step_to(hass, freezer, start + timedelta(days=2, seconds=2))
    assert aioclient_mock.call_count == 3
    server.first = date(2026, 10, 16)
    await _step_to(hass, freezer, start + timedelta(days=3, seconds=3))
    assert aioclient_mock.call_count == 4
    assert "Das Erste: Formel 1 2026-10-18" in await _summaries(hass)
