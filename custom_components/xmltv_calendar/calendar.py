"""Calendar platform: one entity (and one device) per calendar subentry."""

import logging
from datetime import timedelta
from functools import partial
from typing import TYPE_CHECKING, override

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, EVENT_NEW_MATCH, MAX_NEW_MATCH_EVENTS, SUBENTRY_TYPE_CALENDAR
from .coordinator import XmltvCoordinator
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
from .xmltv.model import Channel
from .xmltv.settings import KEY_RETENTION_DAYS, with_defaults
from .xmltv.window import MatchIndex

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from datetime import datetime

    from homeassistant.config_entries import ConfigSubentry
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .data import XmltvConfigEntry
    from .xmltv.matches import RetainedMatch
    from .xmltv.model import EpgData, Programme

_LOGGER = logging.getLogger(__name__)

# The coordinator centralizes updates
PARALLEL_UPDATES = 0

# Hard cap per get_events query (T-01-08): an all-channels calendar can match tens of thousands of programmes
MAX_EVENTS_PER_QUERY = 5000
# CalendarEvent construction costs about 34 µs each; larger slices are built in the executor (RESEARCH Pitfall 5)
EXECUTOR_BUILD_THRESHOLD = 200

# Why a calendar refilters; only new feed data after the entity's first refilter announces new matches (D-10, D-11)
REFILTER_INITIAL = "initial"  # entity added: new calendar, HA start, entry reload (also after source option changes)
REFILTER_DATA = "data"  # the coordinator has new feed data
REFILTER_CONFIG = "config"  # the calendar's filter was edited in place
# Payload keys of the new-match event taken from describe_match (D-07); entity_id and calendar are added
EVENT_MATCH_KEYS = ("title", "summary", "channel", "channel_id", "start", "end", "uid")


def device_info(subentry_id: str, title: str) -> DeviceInfo:
    """Return the device of a calendar subentry, shared by the calendar and its sensors."""
    return DeviceInfo(identifiers={(DOMAIN, subentry_id)}, name=title, entry_type=DeviceEntryType.SERVICE)


def signal_matches(subentry_id: str) -> str:
    """Return the dispatcher signal sent whenever a calendar's matches or templates change."""
    return f"{DOMAIN}_matches_{subentry_id}"


def _to_event(programme: Programme, channels: Mapping[str, Channel], templates: render.EventTemplates) -> CalendarEvent:
    return CalendarEvent(
        start=dt_util.as_local(programme.start),
        end=dt_util.as_local(programme.stop),
        **render.to_event_fields(programme, channels.get(programme.channel_id), templates),
    )


def _channel_map(feed: Mapping[str, Channel], retained: Sequence[RetainedMatch]) -> Mapping[str, Channel]:
    """Return the feed's channels plus the stored names of retained matches' channels the feed lacks (Pitfall 11)."""
    missing = {
        item.programme.channel_id: Channel(item.programme.channel_id, item.channel_name)
        for item in retained
        if item.programme.channel_id not in feed
    }
    return {**feed, **missing} if missing else feed


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


def build_events(
    programmes: Sequence[Programme],
    channels: Mapping[str, Channel],
    templates: render.EventTemplates = render.DEFAULT_TEMPLATES,
) -> list[CalendarEvent]:
    """Build calendar events for one requested slice of matches; safe to run in the executor."""
    # A match whose CalendarEvent cannot be built, whether it fails validation or is out of datetime range after the
    # local-time conversion, is skipped, so it cannot break a read or trigger poll (T-01-09, CR-01)
    events: list[CalendarEvent] = []
    for programme in programmes:
        try:
            events.append(_to_event(programme, channels, templates))
        except HomeAssistantError, OverflowError, ValueError:
            _LOGGER.debug("Skipping invalid programme on %s at %s", programme.channel_id, programme.start)
    return events


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: XmltvConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add one calendar per subentry and keep the callback for subentries added later."""
    runtime = entry.runtime_data
    runtime.add_entities[Platform.CALENDAR] = async_add_entities
    for subentry_id, subentry in entry.subentries.items():
        if subentry.subentry_type != SUBENTRY_TYPE_CALENDAR or subentry_id in runtime.calendars:
            continue
        entity = XmltvCalendarEntity(runtime.coordinator, entry, subentry)
        runtime.calendars[subentry_id] = entity
        async_add_entities([entity], config_subentry_id=subentry_id)


class XmltvCalendarEntity(CoordinatorEntity[XmltvCoordinator], CalendarEntity):
    """A calendar showing the source's programmes that pass the subentry's filter."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, coordinator: XmltvCoordinator, entry: XmltvConfigEntry, subentry: ConfigSubentry) -> None:
        """Initialize from the calendar subentry (D-10, D-11)."""
        super().__init__(coordinator)
        self._entry = entry
        self._subentry_id = subentry.subentry_id
        # The (title, data) the entity was built from: the diff base of differs_from (D-04)
        self._subentry_title = subentry.title
        self._subentry_data = subentry.data
        self._spec = _build_spec(subentry.data, subentry.title)
        self._templates = render.EventTemplates.from_mapping(subentry.data)
        self._retention_days: int = with_defaults(subentry.data)[KEY_RETENTION_DAYS]
        self._attr_unique_id = subentry.subentry_id
        self._attr_device_info = device_info(subentry.subentry_id, subentry.title)
        self._epg: EpgData | None = None
        # Feed channels plus the names of retained matches' channels: used for every rendering (Pitfall 11)
        self._channels: Mapping[str, Channel] = {}
        # The current feed's matches; the previous run's are capture candidates, the parser drops them later (Pitfall 4)
        self._feed_matches: tuple[Programme, ...] = ()
        # Retained programmes merged into the index in addition to the feed's matches (D-18)
        self._retained_shown: frozenset[Programme] = frozenset()
        self._index = MatchIndex(())
        self._generation = 0
        # True once a refilter completed: the matches it saw are the silent baseline (D-10)
        self._baseline_ready = False

    @override
    async def async_added_to_hass(self) -> None:
        """Filter the current data once the entity exists."""
        await super().async_added_to_hass()
        await self._async_refilter(REFILTER_INITIAL)

    @override
    async def async_will_remove_from_hass(self) -> None:
        """
        Discard refilters still in flight.

        Unload flushes the match store after the entities are gone, and HA waits for entry tasks only afterwards: a late
        run must not write to the old store (RESEARCH Pitfall 3) or bring back the record of a removed calendar.
        """
        self._generation += 1
        await super().async_will_remove_from_hass()

    @property
    @override
    def available(self) -> bool:
        """Available while last good data exists, also when the latest refresh failed (D-19)."""
        return self.coordinator.data is not None

    @callback
    @override
    def _handle_coordinator_update(self) -> None:
        """Re-filter in the executor when the coordinator has new data; otherwise only rewrite the state."""
        if self.coordinator.data is self._epg:
            # Unchanged data, e.g. a success/failure transition: the matches are still valid (RESEARCH Pattern 5)
            self.async_write_ha_state()
            return
        self._entry.async_create_task(
            self.hass, self._async_refilter(REFILTER_DATA), name=f"{DOMAIN} refilter {self.entity_id}"
        )

    async def _async_refilter(self, reason: str) -> None:
        """
        Apply the filter off the loop; a newer run wins over an older one still in flight.

        Every match joins the calendar's persisted seen-set. Unseen future matches are announced only for new feed
        data after a baseline exists, so additions, restarts, reloads and edits stay silent (D-08..D-11). A config
        refilter that supersedes an in-flight data refilter absorbs that run's new matches silently: rare, an edit
        during a refresh (RESEARCH Pattern 1).
        """
        self._generation += 1
        generation = self._generation
        epg = self.coordinator.data
        if epg is None:
            return
        if self._spec is None:  # stored pattern does not compile: no matches, other calendars unaffected
            self._epg = epg
            self._channels = epg.channels
            self._feed_matches = ()
            self._retained_shown = frozenset()
            self._index = MatchIndex(())
            self._baseline_ready = True
            self.async_write_ha_state()
            async_dispatcher_send(self.hass, signal_matches(self._subentry_id))
            return
        # Window and weekdays use Home Assistant's configured time zone (D-10); the executor helper takes no kwargs
        result = await self.hass.async_add_executor_job(
            partial(self._spec.apply, epg, tz=dt_util.get_default_time_zone())
        )
        if generation != self._generation:
            return
        store = self._entry.runtime_data.match_store
        record = store.get(self._subentry_id)
        now = dt_util.utcnow()
        cutoff = now - timedelta(days=self._retention_days)
        # Ended matches of the previous and the new run are retained: the parser drops programmes that ended more than
        # a day ago, so the previous run may hold the only copy (D-16, RESEARCH Pitfall 4)
        retained = (
            capture_ended(
                record.retained, (*self._feed_matches, *result.matches), {**self._channels, **epg.channels}, now
            )
            if self._retention_days > 0
            else ()
        )
        retained = prune_retained(retained, cutoff)
        new, seen = new_matches(result.matches, record.seen, now)
        # Entries ended before the retention window can never fire again (D-13)
        store.put(self._subentry_id, CalendarMatches(seen=prune_seen(seen, cutoff), retained=retained))
        fire = reason == REFILTER_DATA and self._baseline_ready
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
        self.async_write_ha_state()
        async_dispatcher_send(self.hass, signal_matches(self._subentry_id))
        if fire:
            self._fire_new_match_events(new)

    def _fire_new_match_events(self, new: Sequence[Programme]) -> None:
        """
        Fire one xmltv_calendar_new_match event per new match with JSON-safe values (D-07, Pitfall 6).

        At most MAX_NEW_MATCH_EVENTS fire, earliest start first; the rest are already in the seen-set (D-12).
        """
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
                    "entity_id": self.entity_id,
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
        values = render.template_values(programme, self._channels.get(programme.channel_id))
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
        return len(self._retained_shown)

    def differs_from(self, subentry: ConfigSubentry) -> bool:
        """Return whether `subentry` has another title or data than the entity was last built from."""
        return (subentry.title, subentry.data) != (self._subentry_title, self._subentry_data)

    async def async_apply_subentry(self, subentry: ConfigSubentry) -> None:
        """Apply an edited calendar subentry in place: rename the device, rebuild filter and templates (D-04)."""
        refilter = False
        write_state = False
        if subentry.data != self._subentry_data:
            # Templates only change the event text: rebuilt without a refilter (EVT-03, EVT-04)
            templates = render.EventTemplates.from_mapping(subentry.data)
            write_state = templates != self._templates
            self._templates = templates
            spec = _build_spec(subentry.data, self.entity_id or subentry.title)
            if spec is not None:  # an uncompilable stored pattern keeps the previous filter and matches (T-02-01)
                self._spec = spec
                refilter = True
        # Store the new diff base before awaiting, so a concurrent listener call sees this edit as applied and the
        # same corrupt data is not retried and re-logged on every later listener call
        self._subentry_data = subentry.data
        if subentry.title != self._subentry_title:
            self._subentry_title = subentry.title
            self._attr_device_info = device_info(self._subentry_id, subentry.title)
            if self.hass is not None:
                # The friendly name follows the device name by itself; the entity_id stays the same
                registry = dr.async_get(self.hass)
                device = registry.async_get_device_by_identifier((DOMAIN, self._subentry_id), self._entry.entry_id)
                if device is not None:
                    registry.async_update_device(device.id, name=subentry.title)
        if self.hass is None:  # not added yet: async_added_to_hass filters (Pitfall 10)
            return
        if refilter:
            await self._async_refilter(REFILTER_CONFIG)
        elif write_state:  # a refilter sends the signal itself
            self.async_write_ha_state()
            async_dispatcher_send(self.hass, signal_matches(self._subentry_id))

    @property
    @override
    def event(self) -> CalendarEvent | None:
        """Return the programme airing now, else the next one; computed live from the current time (AUT-02)."""
        programme = self._index.current_or_next(dt_util.now())
        if programme is None:
            return None
        try:
            return _to_event(programme, self._channels, self._templates)
        except HomeAssistantError, OverflowError, ValueError:
            _LOGGER.debug("Skipping invalid programme on %s", programme.channel_id)
            return None

    @override
    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Return the matches overlapping the requested range, capped and built off the loop when large."""
        if self._epg is None:
            return []
        channels = self._channels
        programmes = self._index.overlapping(start_date, end_date)
        if len(programmes) > MAX_EVENTS_PER_QUERY:
            _LOGGER.debug(
                "Calendar %s: %d matches between %s and %s, returning the first %d",
                self.entity_id,
                len(programmes),
                start_date,
                end_date,
                MAX_EVENTS_PER_QUERY,
            )
            programmes = programmes[:MAX_EVENTS_PER_QUERY]
        if len(programmes) > EXECUTOR_BUILD_THRESHOLD:
            return await hass.async_add_executor_job(build_events, programmes, channels, self._templates)
        return build_events(programmes, channels, self._templates)
