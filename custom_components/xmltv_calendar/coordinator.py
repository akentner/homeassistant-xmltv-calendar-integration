"""One coordinator per source: download and parse the feed, shared by all calendars of the source."""

import io
import logging
from contextlib import contextmanager
from functools import partial
from typing import TYPE_CHECKING, override

from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .cache import CacheMeta, FeedCache, cache_key
from .const import (
    CONF_PATH,
    CONF_SOURCE_TYPE,
    CONF_URL,
    DEFAULT_DURATION,
    DOMAIN,
    KEEP_PAST,
    SOURCE_TYPE_FILE,
    SOURCE_TYPE_URL,
)
from .source import (
    FileMissingError,
    PathNotAllowedError,
    SourceError,
    SourceTooLargeError,
    async_fetch_url,
    read_and_parse_file,
    source_unique_id,
)
from .xmltv.model import EpgData
from .xmltv.parser import FeedError, FeedTooLargeError, parse
from .xmltv.schedule import MIN_DELAY, Schedule, SourceOptions, fresh_until, is_fresh, next_regular

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from datetime import datetime
    from typing import BinaryIO

    from homeassistant.core import HomeAssistant

    from .data import XmltvConfigEntry

_LOGGER = logging.getLogger(__name__)


class XmltvCoordinator(DataUpdateCoordinator[EpgData]):
    """Fetch the source on its schedule (every N hours or daily at a fixed time) and parse it in the executor."""

    config_entry: XmltvConfigEntry

    def __init__(self, hass: HomeAssistant, entry: XmltvConfigEntry) -> None:
        """Initialize with the schedule from the entry options (D-02, D-13)."""
        self._options = SourceOptions.from_mapping(entry.options)
        self._cache = FeedCache(hass, cache_key(entry))
        # The hashed source the cache must belong to; equals the unique_id of flow-created entries (Pitfall 4)
        if entry.data.get(CONF_SOURCE_TYPE) == SOURCE_TYPE_FILE:
            self._source_id = source_unique_id(SOURCE_TYPE_FILE, entry.data[CONF_PATH])
        else:
            self._source_id = source_unique_id(SOURCE_TYPE_URL, entry.data[CONF_URL])
        now = dt_util.utcnow()
        # Wall-clock target of the next refresh (aware UTC); turned into update_interval when HA arms its timer
        self._next_refresh_at: datetime = next_regular(now, self._schedule())
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{entry.title}",
            update_interval=max(self._next_refresh_at - now, MIN_DELAY),
        )

    @property
    def source_options(self) -> SourceOptions:
        """The validated source options this coordinator runs with."""
        return self._options

    @property
    def next_refresh_at(self) -> datetime:
        """When the next refresh is due (aware UTC)."""
        return self._next_refresh_at

    @property
    def cache_meta(self) -> CacheMeta | None:
        """Metadata of the source's disk cache, None when there is none."""
        return self._cache.meta

    def _schedule(self) -> Schedule:
        """Return the refresh schedule in the current HA time zone (read on every call, D-02)."""
        return self._options.schedule(dt_util.get_default_time_zone())

    @callback
    @override
    def _schedule_refresh(self) -> None:
        """Arm HA's timer for the wall-clock target, so a late re-arm (first listener added) keeps the slot."""
        # Never zero: the update_interval setter treats a falsy value as "no polling"
        self.update_interval = max(self._next_refresh_at - dt_util.utcnow(), MIN_DELAY)
        super()._schedule_refresh()

    @override
    async def _async_setup(self) -> None:
        """Load the cache metadata once, before the first refresh."""
        await self._cache.async_load()

    def _set_regular_target(self) -> None:
        self._next_refresh_at = next_regular(dt_util.utcnow(), self._schedule())

    @override
    async def _async_update_data(self) -> EpgData:
        """Read the source (disk cache, download or allowed local file), then parse it off the event loop."""
        # Every outcome sets exactly one refresh target
        if self.config_entry.data.get(CONF_SOURCE_TYPE) == SOURCE_TYPE_FILE:
            try:
                return await self._async_update_file()
            finally:
                self._set_regular_target()
        if self.data is None:
            cached = await self._async_start_from_cache()
            if cached is not None:
                return cached
        try:
            return await self._async_update_url()
        finally:
            self._set_regular_target()

    async def _async_start_from_cache(self) -> EpgData | None:
        """First refresh: the parsed cache when it belongs to this source and is fresh (SRC-06, D-08), else None."""
        meta = self._cache.valid_meta(self._source_id)
        if meta is None:
            return None
        now = dt_util.utcnow()
        schedule = self._schedule()
        if not is_fresh(meta.fetched_at, now, schedule):
            return None
        epg = await self._async_parse_cached()
        if epg is None:
            return None
        _LOGGER.debug("Source %s: using the disk cache from %s", self.config_entry.title, meta.fetched_at)
        self._next_refresh_at = fresh_until(meta.fetched_at, now, schedule)
        return epg

    def _parser(self) -> Callable[[BinaryIO], EpgData]:
        """Return the feed parser with the current cut-off; looks the module-global `parse` up at call time."""
        return partial(parse, keep_after=dt_util.utcnow() - KEEP_PAST, default_duration=DEFAULT_DURATION)

    async def _async_parse_payload(self, payload: bytes) -> EpgData:
        """Parse a feed body in one executor job; parser errors become `UpdateFailed`."""
        with _feed_errors(self.config_entry.title):
            return await self.hass.async_add_executor_job(self._parser(), io.BytesIO(payload))

    async def _async_parse_cached(self) -> EpgData | None:
        """Parse the cached payload; None when it is missing, does not parse or holds no programmes."""
        payload = await self._cache.async_read()
        if payload is None:
            return None
        try:
            epg = await self._async_parse_payload(payload)
        except UpdateFailed:
            return None
        if not epg.programmes:
            return None
        return epg

    async def _async_update_url(self) -> EpgData:
        """Download the feed, parse it in the executor and cache the body when it holds programmes."""
        now = dt_util.utcnow()
        try:
            fetched = await async_fetch_url(self.hass, self.config_entry.data[CONF_URL])
        except SourceTooLargeError as err:
            _LOGGER.debug("Source %s is too large: %s", self.config_entry.title, err)
            raise UpdateFailed(translation_domain=DOMAIN, translation_key="feed_too_large") from err
        except SourceError as err:
            _LOGGER.debug("Source %s unavailable: %s", self.config_entry.title, err)
            raise UpdateFailed(translation_domain=DOMAIN, translation_key="unable_to_fetch") from err
        epg = await self._async_parse_payload(fetched.payload)
        if epg.programmes:
            await self._cache.async_write(
                fetched.payload,
                source_id=self._source_id,
                fetched_at=now,
                etag=fetched.etag,
                last_modified=fetched.last_modified,
            )
        return epg

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
