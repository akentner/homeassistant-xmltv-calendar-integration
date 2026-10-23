"""Runtime data stored on a source config entry."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry

if TYPE_CHECKING:
    from homeassistant.const import Platform
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .calendar import XmltvCalendarEntity
    from .coordinator import XmltvCoordinator
    from .match_store import MatchStore
    from .matcher import CalendarMatcher


@dataclass
class XmltvRuntimeData:
    """The source's coordinator plus the bookkeeping of the diffing update listener."""

    coordinator: XmltvCoordinator
    source_snapshot: tuple[dict[str, Any], dict[str, Any]]
    # Persisted per-calendar match records (new-match seen-set, EVT-08)
    match_store: MatchStore
    matchers: dict[str, CalendarMatcher] = field(default_factory=dict)
    # A suspended update listener must not add entities after successful unload/replacement.
    active: bool = True
    calendars: dict[str, XmltvCalendarEntity] = field(default_factory=dict)
    # One callback per set-up platform: the listener adds entities for subentries added later (RESEARCH Pitfall 2)
    add_entities: dict[Platform, AddConfigEntryEntitiesCallback] = field(default_factory=dict)
    # Subentry IDs whose sensors exist
    sensors: set[str] = field(default_factory=set)


type XmltvConfigEntry = ConfigEntry[XmltvRuntimeData]
