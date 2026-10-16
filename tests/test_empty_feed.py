"""A feed without current programmes is a failure: last good data stays, a first setup retries (D-20, SRC-08)."""

from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from homeassistant.config_entries import ConfigEntryState

from .conftest import DOMAIN, FEED_URL

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()
NOW = "2026-10-13T06:00:00+00:00"
NO_PROGRAMMES_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<tv>
  <channel id="daserste.de"><display-name>Das Erste</display-name></channel>
  <channel id="zdf.de"><display-name>ZDF</display-name></channel>
</tv>
"""
# Every programme ended on 2026-10-11, more than a day before NOW, so the parser's keep_after drops them all
PAST_PROGRAMMES_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<tv>
  <channel id="zdf.de"><display-name>ZDF</display-name></channel>
  <programme channel="zdf.de" start="20261011100000 +0000" stop="20261011110000 +0000"><title>Old</title></programme>
</tv>
"""
ONE_PROGRAMME_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<tv>
  <channel id="zdf.de"><display-name>ZDF</display-name></channel>
  <programme channel="zdf.de" start="20261013120000 +0200" stop="20261013124500 +0200"><title>heute</title></programme>
</tv>
"""
pytestmark = pytest.mark.freeze_time(NOW)


def _payload_files(hass: HomeAssistant) -> list[Path]:
    return list(Path(hass.config.cache_path(DOMAIN)).glob("**/*.feed"))


def _serve(aioclient_mock: AiohttpClientMocker, **kwargs: Any) -> None:
    aioclient_mock.clear_requests()
    aioclient_mock.get(FEED_URL, **kwargs)


async def test_first_setup_with_empty_feed_retries(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(NO_PROGRAMMES_FEED)

    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert entry.error_reason_translation_key == "empty_feed"
    assert hass_storage[f"{DOMAIN}.{entry.entry_id}"]["data"]["health"]["last_failure_reason"] == "empty_feed"
    assert hass_storage[f"{DOMAIN}.{entry.entry_id}"]["data"]["meta"] is None
    assert not _payload_files(hass)


async def test_feed_with_only_past_programmes_retries(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(PAST_PROGRAMMES_FEED)

    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert entry.error_reason_translation_key == "empty_feed"
    assert hass_storage[f"{DOMAIN}.{entry.entry_id}"]["data"]["health"]["last_failure_reason"] == "empty_feed"
    assert not _payload_files(hass)


async def test_later_empty_feed_keeps_last_good_data(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: Any,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED)
    coordinator = entry.runtime_data.coordinator
    previous = coordinator.data
    _serve(aioclient_mock, content=NO_PROGRAMMES_FEED)

    freezer.tick(timedelta(hours=1))
    await coordinator.async_refresh()

    assert coordinator.last_update_success is False
    assert coordinator.last_exception is not None
    assert coordinator.last_exception.translation_key == "empty_feed"
    assert coordinator.data is previous
    (payload,) = _payload_files(hass)
    assert payload.read_bytes() == FEED
    assert coordinator.health.consecutive_failures == 1


async def test_fewer_programmes_are_accepted(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: Any,
    setup_xmltv: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_xmltv(FEED)
    coordinator = entry.runtime_data.coordinator
    previous = coordinator.data
    assert len(previous.programmes) == 4
    _serve(aioclient_mock, content=ONE_PROGRAMME_FEED)

    freezer.tick(timedelta(hours=1))
    await coordinator.async_refresh()

    assert coordinator.last_update_success is True
    assert coordinator.data is not previous
    assert len(coordinator.data.programmes) == 1
