"""Immutable data model of a parsed XMLTV feed."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import datetime


@dataclass(slots=True, frozen=True)
class Channel:
    """One `<channel>` element."""

    id: str
    display_name: str  # first display-name element, else the id


@dataclass(slots=True, frozen=True)
class Programme:
    """One `<programme>` element with tz-aware times."""

    channel_id: str
    start: datetime  # tz-aware
    stop: datetime  # tz-aware, never earlier than start
    titles: tuple[str, ...]  # all title elements, document order; titles[0] is the display title
    sub_titles: tuple[str, ...]
    description: str | None
    categories: tuple[str, ...]
    episode: str | None  # raw first episode-num text

    @property
    def title(self) -> str:
        """Return the display title (the first title element)."""
        return self.titles[0]


@dataclass(slots=True)
class ParseStats:
    """Counters collected while parsing and normalizing a feed."""

    programmes: int = 0
    channels: int = 0
    skipped_malformed: int = 0
    duplicates: int = 0
    inferred_stops: int = 0
    dropped_past: int = 0


@dataclass(frozen=True, eq=False)
class EpgData:
    """A parsed feed. `eq=False` so every refresh counts as new data for the coordinator."""

    channels: Mapping[str, Channel]
    programmes: tuple[Programme, ...]  # sorted by (start, channel_id, title)
    stats: ParseStats
