"""The XMLTV Calendar integration: one config entry per source, one subentry per calendar."""

from typing import TYPE_CHECKING

from homeassistant.const import Platform

from .calendar import XmltvCalendarEntity
from .const import SUBENTRY_TYPE_CALENDAR
from .coordinator import XmltvCoordinator
from .data import XmltvConfigEntry, XmltvRuntimeData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

PLATFORMS: list[Platform] = [Platform.CALENDAR]


async def async_setup_entry(hass: HomeAssistant, entry: XmltvConfigEntry) -> bool:
    """Download and parse the source once, then set up one calendar per subentry."""
    coordinator = XmltvCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = XmltvRuntimeData(
        coordinator=coordinator,
        source_snapshot=(dict(entry.data), dict(entry.options)),
    )
    # The only update listener: subentry add/remove and title changes must not re-download the source
    entry.async_on_unload(entry.add_update_listener(_async_entry_updated))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_entry_updated(hass: HomeAssistant, entry: XmltvConfigEntry) -> None:
    """Reload only when the source settings changed; otherwise reconcile calendar subentries in place."""
    runtime = entry.runtime_data
    if (dict(entry.data), dict(entry.options)) != runtime.source_snapshot:
        hass.config_entries.async_schedule_reload(entry.entry_id)
        return
    for subentry_id in set(runtime.calendars) - set(entry.subentries):
        runtime.calendars.pop(subentry_id)  # HA already removed the entity and its device
    if runtime.add_entities is None:  # platform not set up yet: its setup loop picks the subentries up
        return
    for subentry_id, subentry in entry.subentries.items():
        if subentry.subentry_type == SUBENTRY_TYPE_CALENDAR and subentry_id not in runtime.calendars:
            entity = XmltvCalendarEntity(runtime.coordinator, entry, subentry)
            runtime.calendars[subentry_id] = entity
            runtime.add_entities([entity], config_subentry_id=subentry_id)


async def async_unload_entry(hass: HomeAssistant, entry: XmltvConfigEntry) -> bool:
    """Unload the calendar platform."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
