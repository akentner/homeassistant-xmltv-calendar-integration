"""Per-calendar programme filtering."""

import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .model import EpgData, Programme

KEY_CHANNELS = "channels"
KEY_CHANNEL_REGEX = "channel_regex"
KEY_INCLUDE = "include"
KEY_EXCLUDE = "exclude"

# Cheap ReDoS dampener for admin-supplied patterns (T-01-06); matching runs in the executor anyway
MAX_PATTERN_LENGTH = 300
MAX_PATTERN_LINES = 50


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
    """Return the stripped non-blank lines in NFC, matching the NFC feed text from the parser (D-08)."""
    return [unicodedata.normalize("NFC", line) for raw in text.splitlines() if (line := raw.strip())]


def compile_patterns(text: str) -> tuple[re.Pattern[str], ...]:
    """Compile each stripped non-blank line case-insensitively (D-05, D-08). Raises `re.error`."""
    return tuple(re.compile(line, re.IGNORECASE) for line in _lines(text))


def first_invalid_pattern(text: str) -> InvalidPattern | None:
    """Return the first non-blank line that is over a cap or does not compile, or None (FLT-07)."""
    for index, line in enumerate(_lines(text)):
        if index >= MAX_PATTERN_LINES:
            return InvalidPattern(pattern=line, message=f"more than {MAX_PATTERN_LINES} patterns")
        if len(line) > MAX_PATTERN_LENGTH:
            return InvalidPattern(pattern=line, message=f"pattern longer than {MAX_PATTERN_LENGTH} characters")
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


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


@dataclass(frozen=True)
class FilterSpec:
    """Filter settings of one calendar subentry: channel AND (no include OR any include) AND NOT any exclude."""

    channels: frozenset[str]
    channel_patterns: tuple[re.Pattern[str], ...] = ()
    include: tuple[re.Pattern[str], ...] = ()
    exclude: tuple[re.Pattern[str], ...] = ()

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> FilterSpec:
        """Build the spec from stored subentry data; missing keys mean empty."""
        return cls(
            channels=_str_set(data.get(KEY_CHANNELS)),
            channel_patterns=compile_patterns(_text(data.get(KEY_CHANNEL_REGEX))),
            include=compile_patterns(_text(data.get(KEY_INCLUDE))),
            exclude=compile_patterns(_text(data.get(KEY_EXCLUDE))),
        )

    def _channel_selected(self, channel_id: str) -> bool:
        """Match selected IDs OR the channel regex on the ID; both empty selects every channel (D-02)."""
        if not self.channels and not self.channel_patterns:
            return True
        return channel_id in self.channels or any(pattern.search(channel_id) for pattern in self.channel_patterns)

    def _text_matches(self, programme: Programme) -> bool:
        fields = _fields(programme)
        if self.include and not _any_match(self.include, fields):
            return False
        return not (self.exclude and _any_match(self.exclude, fields))

    def apply(self, epg: EpgData) -> FilterResult:
        """Return the matching programmes, each at most once, plus selected IDs the feed lacks (D-04)."""
        selected: dict[str, bool] = {}
        matches: list[Programme] = []
        for programme in epg.programmes:
            channel_ok = selected.get(programme.channel_id)
            if channel_ok is None:
                channel_ok = selected[programme.channel_id] = self._channel_selected(programme.channel_id)
            if channel_ok and self._text_matches(programme):
                matches.append(programme)
        missing = self.channels - epg.channels.keys() - selected.keys()
        return FilterResult(matches=tuple(matches), missing_channels=frozenset(missing))
