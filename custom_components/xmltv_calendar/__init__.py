"""The XMLTV Calendar integration: one config entry per source, one subentry per calendar."""

from typing import TYPE_CHECKING

from homeassistant.const import Platform
from homeassistant.core import callback
from homeassistant.helpers import issue_registry as ir

from .cache import FeedCache, cache_key
from .calendar import XmltvCalendarEntity
from .const import DOMAIN, SUBENTRY_TYPE_CALENDAR
from .coordinator import XmltvCoordinator, issue_id
from .data import XmltvConfigEntry, XmltvRuntimeData
from .match_store import MatchStore
from .matcher import CalendarMatcher
from .sensor import async_add_subentry_sensors

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigSubentry
    from homeassistant.core import HomeAssistant

PLATFORMS: list[Platform] = [Platform.CALENDAR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: XmltvConfigEntry) -> bool:
    """Download and parse the source once, then set up one calendar per subentry."""
    coordinator = XmltvCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    # Loaded before the platforms: entities read their seen-sets in their first refilter (no I/O in constructors)
    match_store = MatchStore(hass, cache_key(entry))
    # Retained programmes are only valid under the timezone options they were parsed with
    options = coordinator.source_options
    await match_store.async_load(
        fingerprint={"naive_timezone": options.naive_timezone, "offset_minutes": options.offset_minutes}
    )
    match_store.retain_only(
        subentry_id
        for subentry_id, subentry in entry.subentries.items()
        if subentry.subentry_type == SUBENTRY_TYPE_CALENDAR
    )
    entry.runtime_data = XmltvRuntimeData(
        coordinator=coordinator,
        source_snapshot=(dict(entry.data), dict(entry.options)),
        match_store=match_store,
    )
    # The only update listener: subentry add, remove and edit (title or data) never re-download the source
    entry.async_on_unload(entry.add_update_listener(_async_entry_updated))
    for subentry_id, subentry in entry.subentries.items():
        if subentry.subentry_type == SUBENTRY_TYPE_CALENDAR:
            matcher = CalendarMatcher(hass, entry, subentry)
            entry.runtime_data.matchers[subentry_id] = matcher
            await matcher.async_start()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    for matcher in entry.runtime_data.matchers.values():
        matcher.async_identity_ready()
    return True


async def _async_entry_updated(hass: HomeAssistant, entry: XmltvConfigEntry) -> None:
    """Reload only when the source settings changed; otherwise reconcile calendar subentries in place."""
    runtime = entry.runtime_data
    if not runtime.active:
        return
    if (dict(entry.data), dict(entry.options)) != runtime.source_snapshot:
        hass.config_entries.async_schedule_reload(entry.entry_id)
        return
    for subentry_id in set(runtime.matchers) - set(entry.subentries):
        runtime.matchers.pop(subentry_id).async_stop(capture=False)
        runtime.calendars.pop(subentry_id, None)  # HA already removed the entities and their device
        runtime.match_store.forget(subentry_id)
    for subentry_id in runtime.sensors - set(entry.subentries):
        runtime.sensors.discard(subentry_id)
    # Edited calendars are applied in place (D-04); listener calls run as concurrent tasks, so iterate over a copy
    for subentry_id, matcher in list(runtime.matchers.items()):
        subentry = entry.subentries.get(subentry_id)
        if subentry is not None and matcher.differs_from(subentry):
            await matcher.async_apply_subentry(subentry)
            if not runtime.active or getattr(entry, "runtime_data", None) is not runtime:
                return
    for subentry_id, subentry in entry.subentries.items():
        if subentry.subentry_type != SUBENTRY_TYPE_CALENDAR:
            continue
        if subentry_id not in runtime.matchers:
            matcher = CalendarMatcher(hass, entry, subentry)
            runtime.matchers[subentry_id] = matcher
            await matcher.async_start()
            # Removal/unload/replacement can finish while the first executor job is held (T-04-24).
            if not runtime.active or getattr(entry, "runtime_data", None) is not runtime:
                return
            if subentry_id not in entry.subentries or runtime.matchers.get(subentry_id) is not matcher:
                continue
        _async_add_presentations(runtime, entry, subentry)


@callback
def _async_add_presentations(runtime: XmltvRuntimeData, entry: XmltvConfigEntry, subentry: ConfigSubentry) -> None:
    """Add presentation objects only after matcher initialization; platform admission is HA's decision."""
    subentry_id = subentry.subentry_id
    # A platform not set up yet has no callback: its own setup loop picks up the subentries (Pitfall 2).
    add_calendar = runtime.add_entities.get(Platform.CALENDAR)
    if add_calendar is not None and subentry_id not in runtime.calendars:
        entity = XmltvCalendarEntity(runtime.coordinator, entry, subentry)
        runtime.calendars[subentry_id] = entity
        add_calendar([entity], config_subentry_id=subentry_id)
    if Platform.SENSOR in runtime.add_entities and subentry_id not in runtime.sensors:
        async_add_subentry_sensors(runtime, entry, subentry)


async def async_unload_entry(hass: HomeAssistant, entry: XmltvConfigEntry) -> bool:
    """Unload the platforms, then write the match store now so a reload never loads stale records (Pitfall 3)."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        for matcher in entry.runtime_data.matchers.values():
            matcher.async_stop()
        entry.runtime_data.active = False
        await entry.runtime_data.match_store.async_flush()
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: XmltvConfigEntry) -> None:
    """Delete the source's cached feed, metadata and health, match store and Repairs issue when it is removed."""
    if (runtime := getattr(entry, "runtime_data", None)) is not None:
        for matcher in runtime.matchers.values():
            matcher.async_stop(capture=False)
        runtime.active = False
    await FeedCache(hass, cache_key(entry)).async_remove()
    await MatchStore(hass, cache_key(entry)).async_remove()
    ir.async_delete_issue(hass, DOMAIN, issue_id(entry.entry_id))
