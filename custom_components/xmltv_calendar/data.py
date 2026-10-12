"""Runtime data stored on a source config entry."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry

if TYPE_CHECKING:
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .calendar import XmltvCalendarEntity
    from .coordinator import XmltvCoordinator


@dataclass
class XmltvRuntimeData:
    """The source's coordinator plus the bookkeeping of the diffing update listener."""

    coordinator: XmltvCoordinator
    source_snapshot: tuple[dict[str, Any], dict[str, Any]]
    calendars: dict[str, XmltvCalendarEntity] = field(default_factory=dict)
    add_entities: AddConfigEntryEntitiesCallback | None = None


type XmltvConfigEntry = ConfigEntry[XmltvRuntimeData]
