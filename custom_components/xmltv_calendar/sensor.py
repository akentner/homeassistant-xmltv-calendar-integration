"""Sensor platform: next-match and last-fetch timestamp sensors on every calendar's device (AUT-03, AUT-06)."""

import logging
from typing import TYPE_CHECKING, Any, override

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import EntityCategory, Platform
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .calendar import device_info, signal_matches
from .const import SUBENTRY_TYPE_CALENDAR
from .coordinator import XmltvCoordinator, signal_attempt

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
        [
            NextMatchSensor(runtime.coordinator, entry, subentry),
            LastFetchSensor(runtime.coordinator, entry, subentry),
        ],
        config_subentry_id=subentry.subentry_id,
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

        A missing matcher has no next match: state unknown and no match attributes (D-02). Matchers are initialized
        before platform setup. The timer is re-armed for the match found; `at` is the start that just passed, so a
        timer firing a little early still moves on.
        """
        self._cancel_start_timer()
        now = dt_util.utcnow() if at is None else max(dt_util.utcnow(), at)
        matcher = self._entry.runtime_data.matchers.get(self._subentry_id)
        programme = matcher.next_match(now) if matcher is not None else None
        if matcher is None or programme is None:
            self._attr_native_value = None
            self._attr_extra_state_attributes = None
            return
        described = matcher.describe_match(programme)
        self._attr_native_value = programme.start
        self._attr_extra_state_attributes = {key: described[key] for key in MATCH_ATTRIBUTES}
        self._unsub_start = async_track_point_in_utc_time(self.hass, self._handle_start, programme.start)


class LastFetchSensor(CoordinatorEntity[XmltvCoordinator], SensorEntity):
    """
    When the source last ran a refresh, what started it and how it ended (AUT-06, D-20..D-24).

    Every calendar of a source shows the same run; only `matches` is the calendar's own. The run record holds
    vocabulary strings, flags and counts only, never the URL, host or path (D-24).
    """

    _attr_has_entity_name = True
    _attr_translation_key = "last_fetch"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    # Counters, sizes, durations and schedule values change on every run; trigger, outcome, status and reason stay in
    # history (T-04-14)
    _unrecorded_attributes = frozenset(
        {
            "bytes",
            "programmes",
            "channels",
            "parse_duration",
            "matches",
            "next_refresh",
            "last_success",
            "consecutive_failures",
            "cache",
            "sent_etag",
            "sent_last_modified",
        }
    )

    def __init__(self, coordinator: XmltvCoordinator, entry: XmltvConfigEntry, subentry: ConfigSubentry) -> None:
        """Initialize on the calendar subentry's device (D-20)."""
        super().__init__(coordinator)
        self._entry = entry
        self._subentry_id = subentry.subentry_id
        self._attr_unique_id = f"{subentry.subentry_id}_last_fetch"
        self._attr_device_info = device_info(subentry.subentry_id, subentry.title)

    @override
    async def async_added_to_hass(self) -> None:
        """Follow every recorded run (also unchanged data, which calls no listeners) and the calendar's matches."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(self.hass, signal_attempt(self._entry.entry_id), self.async_write_ha_state)
        )
        self.async_on_remove(
            async_dispatcher_connect(self.hass, signal_matches(self._subentry_id), self.async_write_ha_state)
        )

    @property
    @override
    def available(self) -> bool:
        """Always available: a failing source is exactly what this sensor has to show."""
        return True

    @property
    @override
    def native_value(self) -> datetime | None:
        """The time the last run started; unknown before the first one."""
        attempt = self.coordinator.last_attempt
        return attempt.time if attempt is not None else None

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """The run's fields in the diagnostics order, then the live schedule values and this calendar's matches."""
        attempt = self.coordinator.last_attempt
        if attempt is None:
            return None
        attributes = attempt.as_dict()
        del attributes["time"]
        health = self.coordinator.health
        matcher = self._entry.runtime_data.matchers.get(self._subentry_id)
        attributes["last_success"] = (
            dt_util.as_local(health.last_success).isoformat() if health.last_success is not None else None
        )
        attributes["next_refresh"] = dt_util.as_local(self.coordinator.next_refresh_at).isoformat()
        attributes["consecutive_failures"] = health.consecutive_failures
        attributes["matches"] = matcher.match_count if matcher is not None else None
        return attributes
