"""Calendar platform: one entity (and one device) per calendar subentry."""

import logging
from typing import TYPE_CHECKING, override

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, SUBENTRY_TYPE_CALENDAR
from .coordinator import XmltvCoordinator
from .xmltv import render, window
from .xmltv.filter import FilterSpec

if TYPE_CHECKING:
    from datetime import datetime

    from homeassistant.config_entries import ConfigSubentry
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .data import XmltvConfigEntry
    from .xmltv.model import EpgData, Programme

_LOGGER = logging.getLogger(__name__)

# The coordinator centralizes updates
PARALLEL_UPDATES = 0


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
        self._subentry_data = subentry.data
        self._attr_unique_id = subentry.subentry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, subentry.subentry_id)},
            name=subentry.title,
            entry_type=DeviceEntryType.SERVICE,
        )
        self._epg: EpgData | None = None
        self._matches: tuple[Programme, ...] = ()
        self._generation = 0

    @override
    async def async_added_to_hass(self) -> None:
        """Filter the current data once the entity exists."""
        await super().async_added_to_hass()
        await self._async_refilter()

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
        subentry = self._entry.subentries.get(self._subentry_id)
        spec = FilterSpec.from_mapping(subentry.data if subentry is not None else self._subentry_data)
        result = await self.hass.async_add_executor_job(spec.apply, epg)
        if generation != self._generation:
            return
        self._epg = epg
        self._matches = result.matches
        if result.missing_channels:
            _LOGGER.warning(
                "Calendar %s: selected channels not in the feed: %s",
                self.entity_id,
                ", ".join(sorted(result.missing_channels)),
            )
        self.async_write_ha_state()

    def _to_event(self, programme: Programme) -> CalendarEvent:
        channels = self._epg.channels if self._epg is not None else {}
        return CalendarEvent(
            start=dt_util.as_local(programme.start),
            end=dt_util.as_local(programme.stop),
            **render.to_event_fields(programme, channels.get(programme.channel_id)),
        )

    @property
    @override
    def event(self) -> CalendarEvent | None:
        """Return the programme airing now, else the next one; computed live from the current time (AUT-02)."""
        programme = window.current_or_next(self._matches, dt_util.now())
        if programme is None:
            return None
        try:
            return self._to_event(programme)
        except HomeAssistantError:
            _LOGGER.debug("Skipping invalid programme on %s", programme.channel_id)
            return None

    @override
    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Return the matches overlapping the requested range."""
        if self._epg is None:
            return []
        events: list[CalendarEvent] = []
        for programme in window.overlapping(self._matches, start_date, end_date):
            try:
                events.append(self._to_event(programme))
            except HomeAssistantError:
                _LOGGER.debug("Skipping invalid programme on %s", programme.channel_id)
        return events
