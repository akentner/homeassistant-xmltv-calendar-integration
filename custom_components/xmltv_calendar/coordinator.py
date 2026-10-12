"""One coordinator per source: download and parse the feed, shared by all calendars of the source."""

import io
import logging
from datetime import timedelta
from functools import partial
from typing import TYPE_CHECKING, override

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import CONF_REFRESH_HOURS, CONF_URL, DEFAULT_DURATION, DEFAULT_REFRESH_HOURS, DOMAIN, KEEP_PAST
from .source import SourceError, async_fetch_url
from .xmltv.model import EpgData
from .xmltv.parser import FeedError, parse

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import XmltvConfigEntry

_LOGGER = logging.getLogger(__name__)


class XmltvCoordinator(DataUpdateCoordinator[EpgData]):
    """Fetch the source on the configured interval and parse it in the executor."""

    config_entry: XmltvConfigEntry

    def __init__(self, hass: HomeAssistant, entry: XmltvConfigEntry) -> None:
        """Initialize with the refresh interval from the entry options (D-13)."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{entry.title}",
            update_interval=timedelta(hours=entry.options.get(CONF_REFRESH_HOURS, DEFAULT_REFRESH_HOURS)),
        )

    @override
    async def _async_update_data(self) -> EpgData:
        """Download the feed, then parse it off the event loop."""
        try:
            payload = await async_fetch_url(self.hass, self.config_entry.data[CONF_URL])
        except SourceError as err:
            _LOGGER.debug("Source %s unavailable: %s", self.config_entry.title, err)
            raise UpdateFailed(translation_domain=DOMAIN, translation_key="unable_to_fetch") from err
        try:
            return await self.hass.async_add_executor_job(
                partial(
                    parse,
                    io.BytesIO(payload),
                    keep_after=dt_util.utcnow() - KEEP_PAST,
                    default_duration=DEFAULT_DURATION,
                )
            )
        except FeedError as err:
            _LOGGER.debug("Source %s returned an invalid feed: %s", self.config_entry.title, err)
            raise UpdateFailed(translation_domain=DOMAIN, translation_key="invalid_feed") from err
