"""Calendar presentation of the runtime-owned subentry matcher."""

import logging
from typing import TYPE_CHECKING, override

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.const import Platform
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import SUBENTRY_TYPE_CALENDAR
from .coordinator import XmltvCoordinator
from .matcher import device_info, signal_matches
from .xmltv import render

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from datetime import datetime

    from homeassistant.config_entries import ConfigSubentry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .data import XmltvConfigEntry
    from .xmltv.filter import FilterSpec
    from .xmltv.model import Channel, Programme
    from .xmltv.window import MatchIndex

_LOGGER = logging.getLogger(__name__)
PARALLEL_UPDATES = 0
MAX_EVENTS_PER_QUERY = 5000
EXECUTOR_BUILD_THRESHOLD = 200


def _to_event(programme: Programme, channels: Mapping[str, Channel], templates: render.EventTemplates) -> CalendarEvent:
    return CalendarEvent(
        start=dt_util.as_local(programme.start),
        end=dt_util.as_local(programme.stop),
        **render.to_event_fields(programme, channels.get(programme.channel_id), templates),
    )


def build_events(
    programmes: Sequence[Programme],
    channels: Mapping[str, Channel],
    templates: render.EventTemplates = render.DEFAULT_TEMPLATES,
) -> list[CalendarEvent]:
    """Build a bounded query slice; skip invalid events without breaking reads or trigger polling."""
    events = []
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
    """Add a calendar presentation for each subentry, whether admitted by HA or disabled."""
    runtime = entry.runtime_data
    runtime.add_entities[Platform.CALENDAR] = async_add_entities
    for subentry_id, subentry in entry.subentries.items():
        if subentry.subentry_type != SUBENTRY_TYPE_CALENDAR or subentry_id in runtime.calendars:
            continue
        entity = XmltvCalendarEntity(runtime.coordinator, entry, subentry)
        runtime.calendars[subentry_id] = entity
        async_add_entities([entity], config_subentry_id=subentry_id)


class XmltvCalendarEntity(CoordinatorEntity[XmltvCoordinator], CalendarEntity):
    """A read-only view; entity disable/removal never stops the matcher."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, coordinator: XmltvCoordinator, entry: XmltvConfigEntry, subentry: ConfigSubentry) -> None:
        """Attach to the initialized matcher, without owning its state or listeners."""
        super().__init__(coordinator)
        self._matcher = entry.runtime_data.matchers[subentry.subentry_id]
        self._attr_unique_id = subentry.subentry_id
        self._attr_device_info = device_info(subentry.subentry_id, subentry.title)

    @override
    async def async_added_to_hass(self) -> None:
        """Follow index/template signals; the matcher is already initialized."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(self.hass, signal_matches(self._attr_unique_id), self.async_write_ha_state)
        )
        self._matcher.async_identity_ready()

    @property
    @override
    def available(self) -> bool:
        """Keep last good data visible through refresh failures."""
        return self._matcher.has_data

    def next_match(self, now: datetime) -> Programme | None:
        """Compatibility facade for the next-match consumer."""
        return self._matcher.next_match(now)

    def describe_match(self, programme: Programme) -> dict[str, str | None]:
        """Describe the same matcher result used by events."""
        return self._matcher.describe_match(programme)

    @property
    def match_count(self) -> int:
        """Feed match count, also available before entity admission."""
        return self._matcher.match_count

    @property
    def retained_count(self) -> int:
        """Store-only matches inside the retention window."""
        return self._matcher.retained_count

    def differs_from(self, subentry: ConfigSubentry) -> bool:
        """Compare against the runtime's last applied settings."""
        return self._matcher.differs_from(subentry)

    async def async_apply_subentry(self, subentry: ConfigSubentry) -> None:
        """Compatibility delegation for callers applying an in-place edit."""
        await self._matcher.async_apply_subentry(subentry)

    # Read compatibility for existing runtime regression tests; there is only one index and filter owner.
    @property
    def _index(self) -> MatchIndex:
        return self._matcher._index  # noqa: SLF001 -- compatibility facade, no independent state

    @_index.setter
    def _index(self, value: MatchIndex) -> None:
        self._matcher._index = value  # noqa: SLF001 -- compatibility for existing index regression

    @property
    def _spec(self) -> FilterSpec | None:
        return self._matcher._spec  # noqa: SLF001 -- compatibility facade

    @property
    def _feed_matches(self) -> tuple[Programme, ...]:
        return self._matcher._feed_matches  # noqa: SLF001 -- compatibility facade

    @property
    def _retained_shown(self) -> frozenset[Programme]:
        return self._matcher._retained_shown  # noqa: SLF001 -- compatibility facade

    @property
    @override
    def event(self) -> CalendarEvent | None:
        """Return the live current/next match with the current templates."""
        programme = self._matcher.current_or_next(dt_util.now())
        if programme is None:
            return None
        try:
            return _to_event(programme, self._matcher.channels, self._matcher.templates)
        except HomeAssistantError, OverflowError, ValueError:
            _LOGGER.debug("Skipping invalid programme on %s", programme.channel_id)
            return None

    @override
    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Return a capped overlapping slice, building large slices off the event loop."""
        programmes = self._matcher.overlapping(start_date, end_date)
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
            return await hass.async_add_executor_job(
                build_events, programmes, self._matcher.channels, self._matcher.templates
            )
        return build_events(programmes, self._matcher.channels, self._matcher.templates)
