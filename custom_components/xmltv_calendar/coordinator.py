"""One coordinator per source: download and parse the feed, shared by all calendars of the source."""

import io
import logging
from contextlib import contextmanager
from datetime import timedelta
from functools import partial
from typing import TYPE_CHECKING, override

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_PATH,
    CONF_REFRESH_HOURS,
    CONF_SOURCE_TYPE,
    CONF_URL,
    DEFAULT_DURATION,
    DEFAULT_REFRESH_HOURS,
    DOMAIN,
    KEEP_PAST,
    SOURCE_TYPE_FILE,
)
from .source import (
    FileMissingError,
    PathNotAllowedError,
    SourceError,
    SourceTooLargeError,
    async_fetch_url,
    read_and_parse_file,
)
from .xmltv.model import EpgData
from .xmltv.parser import FeedError, FeedTooLargeError, parse

if TYPE_CHECKING:
    from collections.abc import Iterator

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
        """Read the source (download or allowed local file), then parse it off the event loop."""
        if self.config_entry.data.get(CONF_SOURCE_TYPE) == SOURCE_TYPE_FILE:
            return await self._async_update_file()
        return await self._async_update_url()

    async def _async_update_url(self) -> EpgData:
        """Download the feed, then parse it in the executor."""
        try:
            payload = await async_fetch_url(self.hass, self.config_entry.data[CONF_URL])
        except SourceTooLargeError as err:
            _LOGGER.debug("Source %s is too large: %s", self.config_entry.title, err)
            raise UpdateFailed(translation_domain=DOMAIN, translation_key="feed_too_large") from err
        except SourceError as err:
            _LOGGER.debug("Source %s unavailable: %s", self.config_entry.title, err)
            raise UpdateFailed(translation_domain=DOMAIN, translation_key="unable_to_fetch") from err
        with _feed_errors(self.config_entry.title):
            return await self.hass.async_add_executor_job(
                partial(
                    parse,
                    io.BytesIO(payload),
                    keep_after=dt_util.utcnow() - KEEP_PAST,
                    default_duration=DEFAULT_DURATION,
                )
            )

    async def _async_update_file(self) -> EpgData:
        """Check and read the local file in one executor job; the allowed-path check runs on every refresh."""
        try:
            with _feed_errors(self.config_entry.title):
                return await self.hass.async_add_executor_job(
                    partial(
                        read_and_parse_file,
                        self.hass.config,
                        self.config_entry.data[CONF_PATH],
                        keep_after=dt_util.utcnow() - KEEP_PAST,
                        default_duration=DEFAULT_DURATION,
                    )
                )
        except PathNotAllowedError as err:
            _LOGGER.debug("Source %s: %s", self.config_entry.title, err)
            raise UpdateFailed(translation_domain=DOMAIN, translation_key="path_not_allowed") from err
        except FileMissingError as err:
            _LOGGER.debug("Source %s: %s", self.config_entry.title, err)
            raise UpdateFailed(translation_domain=DOMAIN, translation_key="file_not_found") from err
        except SourceError as err:
            _LOGGER.debug("Source %s unavailable: %s", self.config_entry.title, err)
            raise UpdateFailed(translation_domain=DOMAIN, translation_key="unable_to_fetch") from err


@contextmanager
def _feed_errors(title: str) -> Iterator[None]:
    """Translate parser errors into `UpdateFailed` with their translation keys."""
    try:
        yield
    except FeedTooLargeError as err:
        _LOGGER.debug("Source %s is too large: %s", title, err)
        raise UpdateFailed(translation_domain=DOMAIN, translation_key="feed_too_large") from err
    except FeedError as err:
        _LOGGER.debug("Source %s returned an invalid feed: %s", title, err)
        raise UpdateFailed(translation_domain=DOMAIN, translation_key="invalid_feed") from err
