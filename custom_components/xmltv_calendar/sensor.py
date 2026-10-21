"""Sensor platform: a next-match timestamp sensor on every calendar's device (AUT-03)."""

import logging
from typing import TYPE_CHECKING, override

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import Platform
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .calendar import device_info, signal_matches
from .const import SUBENTRY_TYPE_CALENDAR
from .coordinator import XmltvCoordinator

if TYPE_CHECKING:
    from datetime import datetime

    from homeassistant.config_entries import ConfigSubentry
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .data import XmltvConfigEntry, XmltvRuntimeData

_LOGGER = logging.getLogger(__name__)

# The coordinator and the calendar's signal drive all updates
PARALLEL_UPDATES = 0

# The match attributes of the next-match sensor (D-03); the calendar's describe_match also returns the uid
MATCH_ATTRIBUTES = ("title", "summary", "channel", "channel_id", "start", "end", "subtitle", "episode", "description")


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: XmltvConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the sensors of every calendar subentry and keep the callback for subentries added later."""
    runtime = entry.runtime_data
    runtime.add_entities[Platform.SENSOR] = async_add_entities
    for subentry_id, subentry in entry.subentries.items():
        if subentry.subentry_type == SUBENTRY_TYPE_CALENDAR and subentry_id not in runtime.sensors:
            async_add_subentry_sensors(runtime, entry, subentry)


@callback
def async_add_subentry_sensors(runtime: XmltvRuntimeData, entry: XmltvConfigEntry, subentry: ConfigSubentry) -> None:
    """Create the sensors of one calendar subentry on its device; the sensor platform must be set up."""
    runtime.sensors.add(subentry.subentry_id)
    runtime.add_entities[Platform.SENSOR](
        [NextMatchSensor(runtime.coordinator, entry, subentry)], config_subentry_id=subentry.subentry_id
    )


class NextMatchSensor(CoordinatorEntity[XmltvCoordinator], SensorEntity):
    """The start of the calendar's next match that has not started yet (D-01)."""

    _attr_has_entity_name = True
    _attr_translation_key = "next_match"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    # Long feed texts that change with every match and add nothing to history (D-04, T-04-01)
    _unrecorded_attributes = frozenset({"description", "subtitle", "episode"})

    def __init__(self, coordinator: XmltvCoordinator, entry: XmltvConfigEntry, subentry: ConfigSubentry) -> None:
        """Initialize on the calendar subentry's device (D-05)."""
        super().__init__(coordinator)
        self._entry = entry
        self._subentry_id = subentry.subentry_id
        self._attr_unique_id = f"{subentry.subentry_id}_next_match"
        self._attr_device_info = device_info(subentry.subentry_id, subentry.title)
        self._unsub_start: CALLBACK_TYPE | None = None

    @override
    async def async_added_to_hass(self) -> None:
        """Follow the calendar's match changes and compute the first value."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(self.hass, signal_matches(self._subentry_id), self._handle_matches_changed)
        )
        self.async_on_remove(self._cancel_start_timer)
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
    def _handle_start(self, point: datetime) -> None:
        """Move on at the current next match's start; it no longer counts once it airs (D-01, D-06)."""
        self._unsub_start = None
        self._recompute(point)
        self.async_write_ha_state()

    @callback
    def _cancel_start_timer(self) -> None:
        if self._unsub_start is not None:
            self._unsub_start()
            self._unsub_start = None

    @callback
    def _recompute(self, at: datetime | None = None) -> None:
        """
        Set value and attributes from one next-match lookup, so they always describe the same match.

        A calendar not created yet (concurrent platform setup, Pitfall 1) has no next match: state unknown and no
        match attributes (D-02). The timer is re-armed for the match found; `at` is the start that just passed, so a
        timer firing a little early still moves on.
        """
        self._cancel_start_timer()
        now = dt_util.utcnow() if at is None else max(dt_util.utcnow(), at)
        calendar = self._entry.runtime_data.calendars.get(self._subentry_id)
        programme = calendar.next_match(now) if calendar is not None else None
        if calendar is None or programme is None:
            self._attr_native_value = None
            self._attr_extra_state_attributes = None
            return
        described = calendar.describe_match(programme)
        self._attr_native_value = programme.start
        self._attr_extra_state_attributes = {key: described[key] for key in MATCH_ATTRIBUTES}
        self._unsub_start = async_track_point_in_utc_time(self.hass, self._handle_start, programme.start)
