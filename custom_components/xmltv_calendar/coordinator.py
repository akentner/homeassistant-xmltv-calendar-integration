"""One coordinator per source: download and parse the feed, shared by all calendars of the source."""

import io
import logging
from contextlib import contextmanager
from datetime import UTC, timedelta
from functools import partial
from typing import TYPE_CHECKING, override

from homeassistant.core import callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .cache import CacheMeta, FeedCache, SourceHealth, cache_key, payload_sha256
from .const import (
    CONF_PATH,
    CONF_SOURCE_TYPE,
    CONF_URL,
    DEFAULT_DURATION,
    DOMAIN,
    KEEP_PAST,
    NAIVE_TZ_LOCAL,
    SOURCE_TYPE_FILE,
    SOURCE_TYPE_URL,
)
from .source import (
    FileMissingError,
    NotModified,
    PathNotAllowedError,
    SourceError,
    SourceTooLargeError,
    async_fetch_url,
    read_and_parse_file,
    source_unique_id,
)
from .xmltv.model import EpgData
from .xmltv.parser import FeedError, FeedTooLargeError, parse
from .xmltv.schedule import (
    MIN_DELAY,
    Schedule,
    SourceOptions,
    backoff_delay,
    fresh_until,
    is_fresh,
    is_persistently_failing,
    next_regular,
    refresh_base,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from datetime import datetime
    from typing import BinaryIO

    from homeassistant.core import HomeAssistant

    from .data import XmltvConfigEntry
    from .source import Fetched

_LOGGER = logging.getLogger(__name__)

# Translation keys of the coordinator's UpdateFailed; each has an issue text source_failing_<reason>
FAILURE_REASONS = frozenset(
    {"unable_to_fetch", "invalid_feed", "feed_too_large", "path_not_allowed", "file_not_found", "empty_feed"}
)
_DEFAULT_REASON = "unable_to_fetch"


def issue_id(entry_id: str) -> str:
    """Return the id of the Repairs issue a persistently failing source raises (one per source entry)."""
    return f"source_failing_{entry_id}"


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
        # (st_mtime_ns, st_size) of the local file behind the data in memory; file sources only (D-11, Pitfall 10)
        self._file_signature: tuple[int, int] | None = None
        now = dt_util.utcnow()
        # Wall-clock target of the next refresh (aware UTC); turned into update_interval when HA arms its timer
        self._next_refresh_at: datetime = next_regular(now, self._schedule())
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{entry.title}",
            update_interval=max(self._next_refresh_at - now, MIN_DELAY),
            # EpgData compares by identity: returning the same object (304, identical body, unchanged file) calls no
            # listeners unless the success state changed (RESEARCH Pattern 5)
            always_update=False,
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

    @property
    def health(self) -> SourceHealth:
        """Refresh outcomes of the source: last success, failure streak and last failure (read-only snapshot)."""
        return self._cache.health

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
        """Target the regular refresh after the one just served; an early-fired timer serves its target (CR-01)."""
        now = dt_util.utcnow()
        base = refresh_base(now, self._next_refresh_at)
        self._next_refresh_at = next_regular(base, self._schedule())

    @override
    async def _async_update_data(self) -> EpgData:
        """
        Read the source (disk cache, download or allowed local file), then parse it off the event loop.

        Every outcome sets exactly one refresh target and is recorded in the source health: a success (also a 304, an
        identical body or an unchanged file) ends a failure streak, clears its Repairs issue (D-17) and returns to the
        regular schedule; a failure keeps the last good data (SRC-08, D-19), extends the streak, may raise the issue
        and retries after a capped backoff (D-10). A failed first refresh without cache is recorded too, so setup
        retries count toward the issue. `UpdateFailed` is re-raised unchanged, so Home Assistant logs it once per
        streak (RESEARCH Pitfall 8).
        """
        is_file = self.config_entry.data.get(CONF_SOURCE_TYPE) == SOURCE_TYPE_FILE
        if not is_file and self.data is None:
            cached = await self._async_start_from_cache()
            if cached is not None:
                # Non-persistent issues are not restored after a restart: re-raise a still-failing source's issue
                self._sync_issue(dt_util.utcnow())
                return cached
        try:
            epg = await (self._async_update_file() if is_file else self._async_update_url())
        except UpdateFailed as err:
            now = dt_util.utcnow()
            await self._async_record_failure(now, err.translation_key)
            # Capped backoff (D-10): 5 min, 15 min, 1 h, 3 h, 6 h ..., never later than the next regular refresh
            failures = self._cache.health.consecutive_failures
            self._next_refresh_at = now + backoff_delay(failures, now, next_regular(now, self._schedule()))
            raise
        self._set_regular_target()
        await self._async_record_success(dt_util.utcnow())
        return epg

    async def _async_record_success(self, now: datetime) -> None:
        """End the failure streak, clear the Repairs issue (D-17); keep the last failure for diagnostics."""
        health = self._cache.health
        await self._cache.async_save_health(
            SourceHealth(
                last_success=now,
                last_failure_at=health.last_failure_at,
                last_failure_reason=health.last_failure_reason,
            )
        )
        ir.async_delete_issue(self.hass, DOMAIN, issue_id(self.config_entry.entry_id))

    async def _async_record_failure(self, now: datetime, reason: str | None) -> None:
        """Record a failed refresh, extend the failure streak and raise the Repairs issue once it is persistent."""
        health = self._cache.health
        await self._cache.async_save_health(
            SourceHealth(
                last_success=health.last_success,
                failing_since=health.failing_since or now,
                last_failure_at=now,
                last_failure_reason=reason if reason in FAILURE_REASONS else _DEFAULT_REASON,
                consecutive_failures=health.consecutive_failures + 1,
            )
        )
        self._sync_issue(now)

    @callback
    def _sync_issue(self, now: datetime) -> None:
        """
        Raise or update the Repairs issue when the failure streak began more than 24 h before `now` (D-17, D-18).

        The issue is info only and names the source title, the last success in local time and the reason through a
        per-reason translation key; it never holds the URL, the path or exception text (T-03-12). Re-creating it with
        another reason replaces it in place.
        """
        health = self._cache.health
        if not is_persistently_failing(health.failing_since, now):
            return
        reason = health.last_failure_reason if health.last_failure_reason in FAILURE_REASONS else _DEFAULT_REASON
        last_success = (
            dt_util.as_local(health.last_success).strftime("%Y-%m-%d %H:%M") if health.last_success is not None else "-"
        )
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            issue_id(self.config_entry.entry_id),
            is_fixable=False,
            is_persistent=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=f"source_failing_{reason}",
            translation_placeholders={"source": self.config_entry.title, "last_success": last_success},
        )

    async def _async_start_from_cache(self) -> EpgData | None:
        """
        First refresh: the parsed cache when it belongs to this source, else None (SRC-06, D-08, D-09).

        Stale-while-revalidate (RESEARCH Pattern 3): a fresh cache is used until it turns stale; a stale one (also a
        daily slot missed since the fetch, D-03) is shown at once and refreshed about `MIN_DELAY` after the first
        calendar subscribes. The network is touched during setup only without a usable cache, so a slow or
        unreachable host never blocks or fails setup when cached data exists.
        """
        meta = self._cache.valid_meta(self._source_id)
        if meta is None:
            return None
        epg = await self._async_parse_cached()
        if epg is None:
            return None
        now = dt_util.utcnow()
        schedule = self._schedule()
        if is_fresh(meta.fetched_at, now, schedule):
            _LOGGER.debug("Source %s: using the fresh disk cache", self.config_entry.title)
            self._next_refresh_at = fresh_until(meta.fetched_at, now, schedule)
        else:
            _LOGGER.debug("Source %s: using the stale disk cache, refreshing soon", self.config_entry.title)
            self._next_refresh_at = now
        return epg

    def _parser(self) -> Callable[[BinaryIO], EpgData]:
        """
        Return the feed parser with the current cut-off and the source's timezone options (SRC-10).

        Looks the module-global `parse` up at call time. Downloads, cached payloads and files all parse through it, so
        the correction is applied once per parse and never to data already in memory.
        """
        options = self._options
        return partial(
            parse,
            keep_after=dt_util.utcnow() - KEEP_PAST,
            default_duration=DEFAULT_DURATION,
            naive_tz=dt_util.get_default_time_zone() if options.naive_timezone == NAIVE_TZ_LOCAL else UTC,
            shift=timedelta(minutes=options.offset_minutes),
        )

    async def _async_parse_payload(self, payload: bytes) -> EpgData:
        """Parse a feed body in one executor job; parser errors become `UpdateFailed`."""
        with _feed_errors(self.config_entry.title):
            return await self.hass.async_add_executor_job(self._parser(), io.BytesIO(payload))

    async def _async_parse_cached(self) -> EpgData | None:
        """
        Parse the cached payload; None when it is unusable.

        A payload that is missing, has the wrong size, does not parse or holds no programmes is dropped, so the caller
        falls through to an unconditional download and a poisoned cache is never retried (T-03-05).
        """
        payload = await self._cache.async_read()
        epg: EpgData | None = None
        if payload is not None:
            try:
                epg = await self._async_parse_payload(payload)
            except UpdateFailed:
                epg = None
        if epg is None or not epg.programmes:
            _LOGGER.debug("Source %s: dropping an unusable disk cache", self.config_entry.title)
            await self._cache.async_drop()
            return None
        return epg

    async def _async_fetch(self, meta: CacheMeta | None) -> Fetched | NotModified:
        """Download the feed, conditional on the validators of `meta`; source errors become `UpdateFailed`."""
        try:
            return await async_fetch_url(
                self.hass,
                self.config_entry.data[CONF_URL],
                etag=meta.etag if meta is not None else None,
                last_modified=meta.last_modified if meta is not None else None,
            )
        except SourceTooLargeError as err:
            _LOGGER.debug("Source %s is too large: %s", self.config_entry.title, err)
            raise UpdateFailed(translation_domain=DOMAIN, translation_key="feed_too_large") from err
        except SourceError as err:
            _LOGGER.debug("Source %s unavailable: %s", self.config_entry.title, err)
            raise UpdateFailed(translation_domain=DOMAIN, translation_key="unable_to_fetch") from err

    async def _async_update_url(self) -> EpgData:
        """
        Download the feed, parse it in the executor and cache the body; a feed without programmes fails (D-20).

        With a usable cache the stored validators are sent (SRC-07); a 304 keeps the data in memory as the identical
        object, without a body or a parse, and counts as a successful refresh.
        """
        now = dt_util.utcnow()
        # Validators only accompany a cache that belongs to this source, never a request without a payload on disk
        meta = self._cache.valid_meta(self._source_id)
        fetched = await self._async_fetch(meta)
        if isinstance(fetched, NotModified):
            if self.data is not None:
                _LOGGER.debug("Source %s unchanged", self.config_entry.title)
                await self._cache.async_touch(now, etag=fetched.etag, last_modified=fetched.last_modified)
                return self.data
            # No data in memory (RESEARCH Pitfall 3): the unchanged feed is the cached payload
            cached = await self._async_parse_cached()
            if cached is not None:
                await self._cache.async_touch(now, etag=fetched.etag, last_modified=fetched.last_modified)
                return cached
            # The unusable cache is dropped by now; ask again without validators, so the source never stays empty
            _LOGGER.debug("Source %s: unchanged, but the cache is unusable; downloading again", self.config_entry.title)
            fetched = await self._async_fetch(None)
            if isinstance(fetched, NotModified):
                raise UpdateFailed(translation_domain=DOMAIN, translation_key="unable_to_fetch")
        elif (
            meta is not None
            and self.data is not None
            and len(fetched.payload) == meta.size
            and await self.hass.async_add_executor_job(payload_sha256, fetched.payload) == meta.sha256
        ):
            # A server without validators sent the cached bytes again: same feed, no parse (RESEARCH A8)
            _LOGGER.debug("Source %s unchanged (identical body)", self.config_entry.title)
            await self._cache.async_touch(now, etag=fetched.etag, last_modified=fetched.last_modified)
            return self.data
        epg = _require_programmes(await self._async_parse_payload(fetched.payload), self.config_entry.title)
        await self._cache.async_write(
            fetched.payload,
            source_id=self._source_id,
            fetched_at=now,
            etag=fetched.etag,
            last_modified=fetched.last_modified,
        )
        return epg

    async def _async_update_file(self) -> EpgData:
        """
        Check and read the local file in one executor job; the allowed-path check runs on every refresh.

        With data in memory, a file whose mtime and size are unchanged is not parsed again: the same data object is
        returned and counts as a successful refresh (D-11). File sources have no payload cache, so a reload parses.
        """
        try:
            with _feed_errors(self.config_entry.title):
                result = await self.hass.async_add_executor_job(
                    partial(
                        read_and_parse_file,
                        self.hass.config,
                        self.config_entry.data[CONF_PATH],
                        parser=self._parser(),
                        known=self._file_signature if self.data is not None else None,
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
        if result.epg is not None:
            epg = _require_programmes(result.epg, self.config_entry.title)
            self._file_signature = result.signature
            return epg
        if self.data is not None:
            _LOGGER.debug("Source %s: file unchanged", self.config_entry.title)
            return self.data
        # Unreachable: a known signature is only passed while data is in memory
        raise UpdateFailed(translation_domain=DOMAIN, translation_key="unable_to_fetch")


def _require_programmes(epg: EpgData, title: str) -> EpgData:
    """
    Return `epg` when it holds programmes, else fail with `empty_feed` (D-20).

    A feed that parses but has no current programmes never replaces the last good data or the cache; on a first
    setup without cache the entry retries. A feed with fewer programmes than before is accepted as it is.
    """
    if not epg.programmes:
        _LOGGER.debug("Source %s returned a feed without current programmes", title)
        raise UpdateFailed(translation_domain=DOMAIN, translation_key="empty_feed")
    return epg


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
