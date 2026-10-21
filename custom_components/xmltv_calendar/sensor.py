"""Sensor platform: a next-match timestamp sensor on every calendar's device (AUT-03)."""

import logging
from typing import TYPE_CHECKING, override

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .calendar import device_info, signal_matches
from .const import SUBENTRY_TYPE_CALENDAR
from .coordinator import XmltvCoordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigSubentry
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .data import XmltvConfigEntry

_LOGGER = logging.getLogger(__name__)

# The coordinator and the calendar's signal drive all updates
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: XmltvConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add one next-match sensor per calendar subentry."""
    runtime = entry.runtime_data
    for subentry_id, subentry in entry.subentries.items():
        if subentry.subentry_type != SUBENTRY_TYPE_CALENDAR:
            continue
        async_add_entities([NextMatchSensor(runtime.coordinator, entry, subentry)], config_subentry_id=subentry_id)


class NextMatchSensor(CoordinatorEntity[XmltvCoordinator], SensorEntity):
    """The start of the calendar's next match that has not started yet (D-01)."""

    _attr_has_entity_name = True
    _attr_translation_key = "next_match"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: XmltvCoordinator, entry: XmltvConfigEntry, subentry: ConfigSubentry) -> None:
        """Initialize on the calendar subentry's device (D-05)."""
        super().__init__(coordinator)
        self._entry = entry
        self._subentry_id = subentry.subentry_id
        self._attr_unique_id = f"{subentry.subentry_id}_next_match"
        self._attr_device_info = device_info(subentry.subentry_id, subentry.title)

    @override
    async def async_added_to_hass(self) -> None:
        """Follow the calendar's match changes and compute the first value."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(self.hass, signal_matches(self._subentry_id), self._handle_matches_changed)
        )
        self._recompute()

    @property
    @override
    def available(self) -> bool:
        """Available while the source has data, like the calendar (D-02)."""
        return self.coordinator.data is not None

    @callback
    def _handle_matches_changed(self) -> None:
        """Recompute after the calendar's matches or templates changed."""
        self._recompute()
        self.async_write_ha_state()

    @callback
    def _recompute(self) -> None:
        """Look up the next match; a calendar not created yet (concurrent platform setup) has none (Pitfall 1)."""
        calendar = self._entry.runtime_data.calendars.get(self._subentry_id)
        programme = calendar.next_match(dt_util.utcnow()) if calendar is not None else None
        self._attr_native_value = programme.start if programme is not None else None
