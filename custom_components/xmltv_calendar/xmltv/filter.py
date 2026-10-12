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


@dataclass(frozen=True)
class FilterSpec:
    """Filter settings of one calendar subentry. Plan 01-03 adds channel regex, include and exclude."""

    channels: frozenset[str]

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> FilterSpec:
        """Build the spec from stored subentry data."""
        return cls(channels=_str_set(data.get(KEY_CHANNELS)))

    def apply(self, epg: EpgData) -> FilterResult:
        """Return the programmes on the selected channels; no channels selected means all (D-02, D-06)."""
        if not self.channels:
            return FilterResult(matches=epg.programmes)
        matches = tuple(p for p in epg.programmes if p.channel_id in self.channels)
        return FilterResult(matches=matches, missing_channels=frozenset(self.channels - epg.channels.keys()))
