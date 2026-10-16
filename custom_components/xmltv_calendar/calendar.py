"""Calendar platform: one entity (and one device) per calendar subentry."""

import logging
from functools import partial
from typing import TYPE_CHECKING, override

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, SUBENTRY_TYPE_CALENDAR
from .coordinator import XmltvCoordinator
from .xmltv import render
from .xmltv.filter import PATTERN_ERRORS, FilterSpec
from .xmltv.window import MatchIndex

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from datetime import datetime

    from homeassistant.config_entries import ConfigSubentry
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .data import XmltvConfigEntry
    from .xmltv.model import Channel, EpgData, Programme

_LOGGER = logging.getLogger(__name__)

# The coordinator centralizes updates
PARALLEL_UPDATES = 0

# Hard cap per get_events query (T-01-08): an all-channels calendar can match tens of thousands of programmes
MAX_EVENTS_PER_QUERY = 5000
# CalendarEvent construction costs about 34 µs each; larger slices are built in the executor (RESEARCH Pitfall 5)
EXECUTOR_BUILD_THRESHOLD = 200


def _to_event(programme: Programme, channels: Mapping[str, Channel], templates: render.EventTemplates) -> CalendarEvent:
    return CalendarEvent(
        start=dt_util.as_local(programme.start),
        end=dt_util.as_local(programme.stop),
        **render.to_event_fields(programme, channels.get(programme.channel_id), templates),
    )


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
    runtime.add_entities = async_add_entities
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
        self._attr_unique_id = subentry.subentry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, subentry.subentry_id)},
            name=subentry.title,
            entry_type=DeviceEntryType.SERVICE,
        )
        self._epg: EpgData | None = None
        self._index = MatchIndex(())
        self._generation = 0

    @override
    async def async_added_to_hass(self) -> None:
        """Filter the current data once the entity exists."""
        await super().async_added_to_hass()
        await self._async_refilter()

    @property
    @override
    def available(self) -> bool:
        """Available while last good data exists, also when the latest refresh failed (D-19)."""
        return self.coordinator.data is not None

    @callback
    @override
    def _handle_coordinator_update(self) -> None:
        """Re-filter in the executor on every coordinator update."""
        self._entry.async_create_task(self.hass, self._async_refilter(), name=f"{DOMAIN} refilter {self.entity_id}")

    async def _async_refilter(self) -> None:
        """Apply the filter off the loop; a newer run wins over an older one still in flight."""
        self._generation += 1
        generation = self._generation
        epg = self.coordinator.data
        if epg is None:
            return
        if self._spec is None:  # stored pattern does not compile: no matches, other calendars unaffected
            self._epg = epg
            self._index = MatchIndex(())
            self.async_write_ha_state()
            return
        # Window and weekdays use Home Assistant's configured time zone (D-10); the executor helper takes no kwargs
        result = await self.hass.async_add_executor_job(
            partial(self._spec.apply, epg, tz=dt_util.get_default_time_zone())
        )
        if generation != self._generation:
            return
        self._epg = epg
        self._index = MatchIndex(result.matches)
        if result.missing_channels:
            _LOGGER.warning(
                "Calendar %s: selected channels not in the feed: %s",
                self.entity_id,
                ", ".join(sorted(result.missing_channels)),
            )
        self.async_write_ha_state()

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
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, self._subentry_id)},
                name=subentry.title,
                entry_type=DeviceEntryType.SERVICE,
            )
            if self.hass is not None:
                # The friendly name follows the device name by itself; the entity_id stays the same
                registry = dr.async_get(self.hass)
                device = registry.async_get_device_by_identifier((DOMAIN, self._subentry_id), self._entry.entry_id)
                if device is not None:
                    registry.async_update_device(device.id, name=subentry.title)
        if self.hass is None:  # not added yet: async_added_to_hass filters (Pitfall 10)
            return
        if refilter:
            await self._async_refilter()
        elif write_state:
            self.async_write_ha_state()

    @property
    @override
    def event(self) -> CalendarEvent | None:
        """Return the programme airing now, else the next one; computed live from the current time (AUT-02)."""
        programme = self._index.current_or_next(dt_util.now())
        if programme is None:
            return None
        try:
            return _to_event(programme, self._epg.channels if self._epg is not None else {}, self._templates)
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
        channels = self._epg.channels
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
