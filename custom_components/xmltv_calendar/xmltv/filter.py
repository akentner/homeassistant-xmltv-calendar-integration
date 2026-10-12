"""Per-calendar programme filtering."""

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .model import EpgData, Programme

KEY_CHANNELS = "channels"
KEY_CHANNEL_REGEX = "channel_regex"
KEY_INCLUDE = "include"
KEY_EXCLUDE = "exclude"


@dataclass(frozen=True, slots=True)
class InvalidPattern:
    """The first pattern line that does not compile."""

    pattern: str
    message: str


@dataclass(frozen=True, slots=True)
class FilterResult:
    """Matching programmes plus selected channel IDs that the feed does not contain (D-04)."""

    matches: tuple[Programme, ...]
    missing_channels: frozenset[str] = frozenset()


def _lines(text: str) -> list[str]:
    return [line for raw in text.splitlines() if (line := raw.strip())]


def compile_patterns(text: str) -> tuple[re.Pattern[str], ...]:
    """Compile each stripped non-blank line case-insensitively (D-05, D-08). Raises `re.error`."""
    return tuple(re.compile(line, re.IGNORECASE) for line in _lines(text))


def first_invalid_pattern(text: str) -> InvalidPattern | None:
    """Return the first line that does not compile, or None."""
    for line in _lines(text):
        try:
            re.compile(line, re.IGNORECASE)
        except re.error as err:
            return InvalidPattern(pattern=line, message=err.msg)
    return None


def _str_set(value: object) -> frozenset[str]:
    if isinstance(value, str):
        return frozenset({value}) if value else frozenset()
    if isinstance(value, Iterable):
        return frozenset(str(item) for item in value if item)
    return frozenset()


def _fields(programme: Programme) -> tuple[str, ...]:
    """Return the matched fields: the title, then each sub-title, each tested on its own (D-07)."""
    return (programme.title, *programme.sub_titles)


def _any_match(patterns: tuple[re.Pattern[str], ...], fields: tuple[str, ...]) -> bool:
    return any(pattern.search(field) for pattern in patterns for field in fields)


@dataclass(frozen=True)
class FilterSpec:
    """Filter settings of one calendar subentry."""

    channels: frozenset[str]
    include: tuple[re.Pattern[str], ...] = ()

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> FilterSpec:
        """Build the spec from stored subentry data."""
        return cls(
            channels=_str_set(data.get(KEY_CHANNELS)),
            include=compile_patterns(str(data.get(KEY_INCLUDE) or "")),
        )

    def _matches(self, programme: Programme) -> bool:
        if self.channels and programme.channel_id not in self.channels:
            return False
        return not self.include or _any_match(self.include, _fields(programme))

    def apply(self, epg: EpgData) -> FilterResult:
        """Return the programmes on the selected channels (none selected = all) that pass include (D-02, D-05)."""
        matches = tuple(p for p in epg.programmes if self._matches(p))
        missing = frozenset(self.channels - epg.channels.keys()) if self.channels else frozenset()
        return FilterResult(matches=matches, missing_channels=missing)
