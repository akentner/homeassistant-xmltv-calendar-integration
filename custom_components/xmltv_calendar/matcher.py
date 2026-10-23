"""Entity-independent matching, events and retention for a calendar subentry."""

import asyncio
import logging
from dataclasses import dataclass, replace
from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util

from .const import DOMAIN, EVENT_NEW_MATCH, MAX_NEW_MATCH_EVENTS
from .xmltv import render
from .xmltv.filter import PATTERN_ERRORS, FilterSpec
from .xmltv.matches import (
    CalendarMatches,
    capture_ended,
    merge_matches,
    new_matches,
    prune_retained,
    prune_seen,
    split_announcements,
)
from .xmltv.model import Channel, EpgData, ParseStats
from .xmltv.settings import KEY_RETENTION_DAYS, with_defaults
from .xmltv.window import MatchIndex

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from datetime import datetime, tzinfo

    from homeassistant.config_entries import ConfigSubentry

    from .data import XmltvConfigEntry
    from .xmltv.filter import FilterResult
    from .xmltv.matches import RetainedMatch
    from .xmltv.model import Programme

_LOGGER = logging.getLogger(__name__)

# Why a matcher refilters; only new feed data after its silent baseline announces matches (D-10, D-11)
REFILTER_INITIAL = "initial"  # new subentry, HA start, entry reload (also after source option changes)
REFILTER_DATA = "data"  # the coordinator has new feed data
REFILTER_CONFIG = "config"  # the calendar's filter was edited in place
# Payload keys of the new-match event taken from describe_match (D-07); entity_id and calendar are added
EVENT_MATCH_KEYS = ("title", "summary", "channel", "channel_id", "start", "end", "uid")


@dataclass(frozen=True, slots=True)
class _ConfigSnapshot:
    """An accepted edit's silent baseline and raw recheck, independent of later DATA."""

    revision: int
    spec: FilterSpec | None
    epg: EpgData | None
    recheck: tuple[Programme, ...]
    retention_days: int
    tz: tzinfo


def device_info(subentry_id: str, title: str) -> DeviceInfo:
    """Return the device of a calendar subentry, shared by the calendar and its sensors."""
    return DeviceInfo(identifiers={(DOMAIN, subentry_id)}, name=title, entry_type=DeviceEntryType.SERVICE)


def signal_matches(subentry_id: str) -> str:
    """Return the dispatcher signal sent whenever a calendar's matches or templates change."""
    return f"{DOMAIN}_matches_{subentry_id}"


def _channel_map(feed: Mapping[str, Channel], retained: Sequence[RetainedMatch]) -> Mapping[str, Channel]:
    """Return the feed's channels plus the stored names of retained matches' channels the feed lacks (Pitfall 11)."""
    missing = {
        item.programme.channel_id: Channel(item.programme.channel_id, item.channel_name)
        for item in retained
        if item.programme.channel_id not in feed
    }
    return {**feed, **missing} if missing else feed


def _apply_filter(
    spec: FilterSpec, epg: EpgData, recheck: tuple[Programme, ...] | None, tz: tzinfo
) -> tuple[FilterResult, frozenset[Programme] | None]:
    """
    Filter the feed, and the retained candidates of a filter edit, in one executor job.

    `recheck` holds the retained programmes and the previous run's matches; the ones the edited filter still matches
    are returned, the others are dropped from retention (D-17). None skips the re-check.
    """
    result = spec.apply(epg, tz=tz)
    if recheck is None:
        return result, None
    kept = spec.apply(EpgData(channels=epg.channels, programmes=recheck, stats=ParseStats()), tz=tz).matches
    return result, frozenset(kept)


def _build_spec(data: Mapping[str, object], name: str) -> FilterSpec | None:
    """
    Build the filter from stored subentry data; None when a hand-edited stored pattern does not compile (T-02-01).

    That covers every way re.compile rejects a pattern: a syntax error, a repeat count that overflows, or nesting
    deep enough to exceed the recursion limit (CR-01).
    """
    try:
        return FilterSpec.from_mapping(data)
    except PATTERN_ERRORS:
        _LOGGER.warning("Calendar %s: stored filter pattern is invalid", name)
        return None


class CalendarMatcher:
    """One runtime-owned filter/index and persisted match record, independent of any enabled entity."""

    def __init__(self, hass: HomeAssistant, entry: XmltvConfigEntry, subentry: ConfigSubentry) -> None:
        """Bind explicitly to the runtime that owns this matcher."""
        self.hass = hass
        self._entry = entry
        self._runtime = entry.runtime_data
        self.coordinator = self._runtime.coordinator
        self._subentry_id = subentry.subentry_id
        # The last applied (title, data): the diff base of differs_from (D-04)
        self._subentry_title = subentry.title
        self._subentry_data = subentry.data
        self._spec = _build_spec(subentry.data, subentry.title)
        self._templates = render.EventTemplates.from_mapping(subentry.data, subentry.title)
        self._retention_days: int = with_defaults(subentry.data)[KEY_RETENTION_DAYS]
        self._epg: EpgData | None = None
        # Feed channels plus the names of retained matches' channels: used for every rendering (Pitfall 11)
        self._channels: Mapping[str, Channel] = {}
        # The current feed's matches; the previous run's are capture candidates, the parser drops them later (Pitfall 4)
        self._feed_matches: tuple[Programme, ...] = ()
        # Retained programmes merged into the index in addition to the feed's matches (D-18)
        self._retained_shown: frozenset[Programme] = frozenset()
        self._index = MatchIndex(())
        self._generation = 0
        self._config_revision = 0
        self._committed_config_revision = 0
        self._config_pending = False
        self._pending_config: _ConfigSnapshot | None = None
        self._refilter_lock = asyncio.Lock()
        # True once a refilter completed: the matches it saw are the silent baseline (D-10)
        self._baseline_ready = False
        self._active = False
        self._unsub_coordinator: CALLBACK_TYPE | None = None
        self._unsub_stop: CALLBACK_TYPE | None = None
        self._identity_ready = False

    async def async_start(self) -> None:
        """Initialize before platform admission; repeated starts never reset the silent baseline."""
        if self._active:
            return
        self._active = True
        self._identity_ready = False
        self._unsub_coordinator = self.coordinator.async_add_listener(self._handle_coordinator_update)
        self._unsub_stop = self.hass.bus.async_listen(EVENT_HOMEASSISTANT_STOP, self._handle_stop)
        await self._async_refilter(REFILTER_INITIAL)

    @callback
    def async_stop(self, *, capture: bool = True) -> None:
        """Capture before invalidating all workers and detaching both runtime listeners."""
        if not self._active:
            return
        if capture:
            self._capture_now()
        self._active = False
        self._generation += 1
        for attr in ("_unsub_coordinator", "_unsub_stop"):
            if (unsub := getattr(self, attr)) is not None:
                unsub()
                setattr(self, attr, None)

    @property
    def entity_id(self) -> str | None:
        """Use the registry identity, including disabled and user-renamed calendars; never invent an ID."""
        return er.async_get(self.hass).async_get_entity_id("calendar", DOMAIN, self._subentry_id)

    @callback
    def async_identity_ready(self) -> None:
        """Open event dispatch only after calendar platform registration completed."""
        if self._is_current():
            self._identity_ready = self.entity_id is not None
            async_dispatcher_send(self.hass, signal_matches(self._subentry_id))

    def _is_current(self) -> bool:
        return (
            self._active
            and self._runtime.active
            and getattr(self._entry, "runtime_data", None) is self._runtime
            and self._runtime.matchers.get(self._subentry_id) is self
            and self._subentry_id in self._entry.subentries
        )

    @callback
    def _handle_stop(self, _event: Event) -> None:
        self.async_stop()

    @callback
    def _capture_now(self) -> None:
        """Add the current feed matches that have ended to the stored retained list; no refilter, no state write."""
        if not self._is_current() or self._retention_days <= 0 or not self._feed_matches:
            return
        store = self._entry.runtime_data.match_store
        record = store.get(self._subentry_id)
        now = dt_util.utcnow()
        retained = prune_retained(
            capture_ended(record.retained, self._feed_matches, self._channels, now),
            now - timedelta(days=self._retention_days),
        )
        if retained != record.retained:
            store.put(self._subentry_id, replace(record, retained=retained))

    @property
    def has_data(self) -> bool:
        """Available while last good data exists, also when the latest refresh failed (D-19)."""
        return self.coordinator.data is not None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Re-filter changed data only while this matcher belongs to the live runtime."""
        if not self._is_current() or (self.coordinator.data is self._epg and not self._config_pending):
            # Unchanged data, e.g. a success/failure transition: the matches are still valid (RESEARCH Pattern 5)
            return
        self._entry.async_create_task(
            self.hass, self._async_refilter(REFILTER_DATA), name=f"{DOMAIN} refilter {self.entity_id}"
        )

    async def _async_refilter(self, reason: str) -> None:
        """Serialize commits; DATA cannot cancel a configuration baseline/recheck obligation."""
        async with self._refilter_lock:
            while self._is_current():
                change = self._pending_config
                if change is None and reason == REFILTER_CONFIG:
                    return  # Another waiter already committed this edit (or a newer one).
                epg = change.epg if change is not None else self.coordinator.data
                if epg is None:
                    return
                if change is None and reason == REFILTER_DATA and epg is self._epg:
                    return
                spec = change.spec if change is not None else self._spec
                revision = self._config_revision
                generation = self._generation
                retention_days = change.retention_days if change is not None else self._retention_days
                tz = change.tz if change is not None else dt_util.get_default_time_zone()
                recheck = change.recheck if change is not None else None
                # Data that arrived before registry admission remains a silent startup baseline.
                identity_ready = self._identity_ready or self.entity_id is not None
                if spec is None:
                    self._epg = epg
                    self._channels = epg.channels
                    self._feed_matches = ()
                    self._retained_shown = frozenset()
                    self._index = MatchIndex(())
                    self._baseline_ready = True
                    if change is not None:
                        self._committed_config_revision = change.revision
                        self._pending_config = None
                        self._config_pending = False
                    async_dispatcher_send(self.hass, signal_matches(self._subentry_id))
                    return
                result, allowed = await self.hass.async_add_executor_job(_apply_filter, spec, epg, recheck, tz)
                if generation != self._generation or not self._is_current():
                    return
                if revision != self._config_revision:
                    # An edit accepted during this worker owns its own feed snapshot and recheck.
                    # Discard stale work, but never discard that newer semantic obligation.
                    continue
                if change is None and epg is not self.coordinator.data:
                    continue  # Coalesce superseded DATA, without cancelling CONFIG's older baseline snapshot.
                fire = change is None and reason == REFILTER_DATA and self._baseline_ready and identity_ready
                self._commit_filter(epg, result, allowed, retention_days, fire=fire)
                if change is None:
                    return
                self._committed_config_revision = change.revision
                self._pending_config = None
                self._config_pending = False
                # A DATA caller interrupted by CONFIG still processes newer data after the silent baseline.
                # A CONFIG caller leaves queued DATA to its own waiter, never repurposing it as config work.

    @callback
    def _commit_filter(
        self,
        epg: EpgData,
        result: FilterResult,
        allowed: frozenset[Programme] | None,
        retention_days: int,
        *,
        fire: bool,
    ) -> None:
        """
        Apply one validated snapshot synchronously to the Store, index and consumers.

        Only DATA against a committed baseline announces; edits and startup still populate seen silently.
        """
        store = self._entry.runtime_data.match_store
        record = store.get(self._subentry_id)
        previous = self._feed_matches
        kept = record.retained
        if allowed is not None:
            kept = tuple(item for item in kept if item.programme in allowed)
            previous = tuple(programme for programme in previous if programme in allowed)
        now = dt_util.utcnow()
        cutoff = now - timedelta(days=retention_days)
        # Ended matches of the previous and the new run are retained: the parser drops programmes that ended more than
        # a day ago, so the previous run may hold the only copy (D-16, RESEARCH Pitfall 4)
        retained = (
            capture_ended(kept, (*previous, *result.matches), {**self._channels, **epg.channels}, now)
            if retention_days > 0
            else ()
        )
        retained = prune_retained(retained, cutoff)
        new, seen = new_matches(result.matches, record.seen, now)
        # Entries ended before the retention window can never fire again (D-13)
        store.put(self._subentry_id, CalendarMatches(seen=prune_seen(seen, cutoff), retained=retained))
        merged = merge_matches(result.matches, retained)
        self._epg = epg
        self._channels = _channel_map(epg.channels, retained)
        self._feed_matches = result.matches
        self._retained_shown = frozenset(merged[len(result.matches) :])
        self._index = MatchIndex(merged)
        self._baseline_ready = True
        if result.missing_channels:
            _LOGGER.warning(
                "Calendar %s: selected channels not in the feed: %s",
                self.entity_id,
                ", ".join(sorted(result.missing_channels)),
            )
        async_dispatcher_send(self.hass, signal_matches(self._subentry_id))
        if fire:
            self._fire_new_match_events(new)

    def _fire_new_match_events(self, new: Sequence[Programme]) -> None:
        """
        Fire one xmltv_calendar_new_match event per new match with JSON-safe values (D-07, Pitfall 6).

        At most MAX_NEW_MATCH_EVENTS fire, earliest start first; the rest are already in the seen-set (D-12).
        """
        entity_id = self.entity_id
        if entity_id is None:
            return
        announced, suppressed = split_announcements(new, MAX_NEW_MATCH_EVENTS)
        if suppressed:
            _LOGGER.warning(
                "Calendar %s: %d new matches not announced (limit %d per refresh)",
                self.entity_id,
                suppressed,
                MAX_NEW_MATCH_EVENTS,
            )
        for programme in announced:
            match = self.describe_match(programme)
            self.hass.bus.async_fire(
                EVENT_NEW_MATCH,
                {
                    "entity_id": entity_id,
                    "calendar": self._subentry_title,
                    **{key: match[key] for key in EVENT_MATCH_KEYS},
                },
            )

    def next_match(self, now: datetime) -> Programme | None:
        """Return the earliest match starting strictly after `now`; an airing match never counts (D-01)."""
        return self._index.next_after(now)

    def describe_match(self, programme: Programme) -> dict[str, str | None]:
        """
        Describe one match for the next-match sensor and the new-match event (D-03).

        title is the raw feed title, summary the title rendered with the calendar's template, start and end are
        ISO 8601 in Home Assistant's local time; values the feed lacks are None.
        """
        values = render.template_values(
            programme, self._channels.get(programme.channel_id), tz=dt_util.get_default_time_zone()
        )
        return {
            "title": programme.title,
            "summary": self._templates.render_title(programme, values),
            "channel": values["channel"],
            "channel_id": programme.channel_id,
            "start": dt_util.as_local(programme.start).isoformat(),
            "end": dt_util.as_local(programme.stop).isoformat(),
            "subtitle": programme.sub_titles[0] if programme.sub_titles else None,
            "episode": programme.episode or None,
            "description": programme.description or None,
            "uid": render.event_uid(programme),
        }

    @property
    def match_count(self) -> int:
        """Number of feed programmes the calendar's filter currently matches (diagnostics, D-19, D-21)."""
        return len(self._feed_matches)

    @property
    def retained_count(self) -> int:
        """Number of retained past matches shown in addition to the feed's matches (diagnostics, D-19)."""
        cutoff = dt_util.utcnow() - timedelta(days=self._retention_days)
        return sum(1 for programme in self._retained_shown if programme.stop >= cutoff)

    def differs_from(self, subentry: ConfigSubentry) -> bool:
        """Return whether `subentry` has another title or data than the entity was last built from."""
        return (subentry.title, subentry.data) != (self._subentry_title, self._subentry_data)

    async def async_apply_subentry(self, subentry: ConfigSubentry) -> None:
        """Apply an edited calendar subentry in place: rename the device, rebuild filter and templates (D-04)."""
        if not self._is_current():
            return
        refilter = False
        write_state = False
        if subentry.data != self._subentry_data:
            # A retention edit applies in place; the refilter re-applies the window (D-14)
            retention_days = with_defaults(subentry.data)[KEY_RETENTION_DAYS]
            refilter = retention_days != self._retention_days
            self._retention_days = retention_days
            # Templates only change the event text: rebuilt without a refilter (EVT-03, EVT-04)
            templates = render.EventTemplates.from_mapping(subentry.data, subentry.title)
            write_state = templates != self._templates
            self._templates = templates
            spec = _build_spec(subentry.data, self.entity_id or subentry.title)
            if spec is not None:  # an uncompilable stored pattern keeps the previous filter and matches (T-02-01)
                refilter = refilter or spec != self._spec
                self._spec = spec
        # Store the new diff base before awaiting, so a concurrent listener call sees this edit as applied and the
        # same corrupt data is not retried and re-logged on every later listener call
        self._subentry_data = subentry.data
        if subentry.title != self._subentry_title:
            self._subentry_title = subentry.title
            # The friendly name follows the device name by itself; the entity_id stays the same.
            registry = dr.async_get(self.hass)
            device = registry.async_get_device_by_identifier((DOMAIN, self._subentry_id), self._entry.entry_id)
            if device is not None:
                registry.async_update_device(device.id, name=subentry.title)
        if refilter:
            self._config_revision += 1
            self._config_pending = True
            self._pending_config = _ConfigSnapshot(
                revision=self._config_revision,
                spec=self._spec,
                epg=self.coordinator.data,
                recheck=(
                    *(item.programme for item in self._runtime.match_store.get(self._subentry_id).retained),
                    *self._feed_matches,
                ),
                retention_days=self._retention_days,
                tz=dt_util.get_default_time_zone(),
            )
            await self._async_refilter(REFILTER_CONFIG)
        elif write_state:  # a refilter sends the signal itself
            async_dispatcher_send(self.hass, signal_matches(self._subentry_id))

    @property
    def channels(self) -> Mapping[str, Channel]:
        """The current feed channels plus retained channel-name fallbacks."""
        return self._channels

    @property
    def templates(self) -> render.EventTemplates:
        """The current presentation templates, also applied to raw retained matches."""
        return self._templates

    def current_or_next(self, now: datetime) -> Programme | None:
        """Return the airing match, else the next one (AUT-02)."""
        return self._index.current_or_next(now)

    def overlapping(self, start_date: datetime, end_date: datetime) -> list[Programme]:
        """Return overlapping matches, hiding expired retention even without a refilter."""
        if self._epg is None:
            return []
        programmes = self._index.overlapping(start_date, end_date)
        if self._retained_shown:
            # A retained programme leaves exactly when its window ends, also while unchanged feeds skip the refilter
            cutoff = dt_util.utcnow() - timedelta(days=self._retention_days)
            programmes = [p for p in programmes if p.stop >= cutoff or p not in self._retained_shown]
        return programmes
