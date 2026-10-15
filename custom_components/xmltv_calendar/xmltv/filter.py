"""Per-calendar programme filtering."""

import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, timedelta
from typing import TYPE_CHECKING

# The stored keys are owned by settings.py; KEY_* stay importable from here for const.py
from .settings import (
    DEFAULT_MATCH_FIELDS,
    FIELD_CATEGORY,
    FIELD_DESCRIPTION,
    FIELD_SUBTITLE,
    FIELD_TITLE,
    KEY_CASE_SENSITIVE,
    KEY_CHANNEL_REGEX,
    KEY_CHANNELS,
    KEY_EXCLUDE,
    KEY_EXCLUDE_FIELDS,
    KEY_INCLUDE,
    KEY_INCLUDE_FIELDS,
    KEY_MAX_DURATION,
    KEY_MIN_DURATION,
    KEY_TIME_FROM,
    KEY_TIME_TO,
    KEY_WEEKDAYS,
    WEEKDAYS,
    with_defaults,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Mapping
    from datetime import date, datetime, tzinfo

    from .model import EpgData, Programme

_DEFAULT_FIELDS = frozenset(DEFAULT_MATCH_FIELDS)

# Cheap ReDoS dampener for admin-supplied patterns (T-01-06); matching runs in the executor anyway
MAX_PATTERN_LENGTH = 300
MAX_PATTERN_LINES = 50

# with_defaults keeps any non-negative int; larger stored minutes would overflow timedelta (clamped, never raised)
_MAX_MINUTES = timedelta.max // timedelta(minutes=1)


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


def _duration(minutes: int | None) -> timedelta | None:
    """Return stored whole minutes as a timedelta, clamped to the largest one; None means unbounded (D-13)."""
    return None if minutes is None else timedelta(minutes=min(minutes, _MAX_MINUTES))


def _minute_of_day(value: str) -> int:
    """Return the minutes after midnight of a stored "HH:MM" value."""
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


@dataclass(frozen=True, slots=True)
class TimeWindow:
    """
    Half-open local time-of-day window [start, end) in minutes after midnight; start > end crosses midnight (D-09).

    Same semantics as Home Assistant's time condition: a start exactly at `end` is outside (user resolution A2).
    """

    start: int
    end: int

    @classmethod
    def from_times(cls, time_from: str | None, time_to: str | None) -> TimeWindow | None:
        """Build the window from stored "HH:MM" bounds; one missing bound or equal bounds mean no window (D-12)."""
        if time_from is None or time_to is None:
            return None
        start, end = _minute_of_day(time_from), _minute_of_day(time_to)
        return cls(start, end) if start != end else None

    def anchor_date(self, local: datetime) -> date | None:
        """
        Return the date the window containing `local` opened on, or None when `local` is outside the window.

        The after-midnight part of a crossing window belongs to the previous day, so a "Friday 22:00-02:00" window
        also matches Saturday 01:00 (D-11).
        """
        minute = local.hour * 60 + local.minute
        if self.start < self.end:
            return local.date() if self.start <= minute < self.end else None
        if minute >= self.start:
            return local.date()
        if minute < self.end:
            return local.date() - timedelta(days=1)
        return None


def _lines(text: str) -> list[str]:
    """Return the stripped non-blank lines in NFC, matching the NFC feed text from the parser (D-08)."""
    return [unicodedata.normalize("NFC", line) for raw in text.splitlines() if (line := raw.strip())]


def _flags(*, case_sensitive: bool) -> int:
    return 0 if case_sensitive else re.IGNORECASE


def compile_patterns(text: str, *, case_sensitive: bool = False) -> tuple[re.Pattern[str], ...]:
    """Compile each stripped non-blank NFC line, ignoring case unless `case_sensitive` (D-08). Raises `re.error`."""
    flags = _flags(case_sensitive=case_sensitive)
    return tuple(re.compile(line, flags) for line in _lines(text))


def first_invalid_pattern(text: str, *, case_sensitive: bool = False) -> InvalidPattern | None:
    """Return the first non-blank line that is over a cap or does not compile, or None (FLT-07)."""
    flags = _flags(case_sensitive=case_sensitive)
    for index, line in enumerate(_lines(text)):
        if index >= MAX_PATTERN_LINES:
            return InvalidPattern(pattern=line, message=f"more than {MAX_PATTERN_LINES} patterns")
        if len(line) > MAX_PATTERN_LENGTH:
            return InvalidPattern(pattern=line, message=f"pattern longer than {MAX_PATTERN_LENGTH} characters")
        try:
            re.compile(line, flags)
        except re.error as err:
            return InvalidPattern(pattern=line, message=err.msg)
    return None


def _field_values(programme: Programme, fields: frozenset[str]) -> Iterator[str]:
    """
    Yield the selected field values, each sub-title and each category on its own (D-05, D-07).

    Order is title, sub-titles, categories, then the description last: it is the most expensive to scan, and callers
    short-circuit with any() (Pitfall 7).
    """
    if FIELD_TITLE in fields:
        yield programme.title
    if FIELD_SUBTITLE in fields:
        yield from programme.sub_titles
    if FIELD_CATEGORY in fields:
        yield from programme.categories
    if FIELD_DESCRIPTION in fields and programme.description:
        yield programme.description


def _any_match(patterns: tuple[re.Pattern[str], ...], values: Iterable[str]) -> bool:
    return any(pattern.search(value) for value in values for pattern in patterns)


@dataclass(frozen=True)
class FilterSpec:
    """Filter settings of one calendar subentry: channel AND (no include OR any include) AND NOT any exclude."""

    channels: frozenset[str]
    channel_patterns: tuple[re.Pattern[str], ...] = ()
    include: tuple[re.Pattern[str], ...] = ()
    exclude: tuple[re.Pattern[str], ...] = ()
    include_fields: frozenset[str] = _DEFAULT_FIELDS
    exclude_fields: frozenset[str] = _DEFAULT_FIELDS
    min_duration: timedelta | None = None
    max_duration: timedelta | None = None
    window: TimeWindow | None = None
    weekdays: frozenset[int] = frozenset()  # datetime.weekday() values; empty = every day

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> FilterSpec:
        """Build the spec from stored subentry data; missing or invalid values mean their defaults (D-06)."""
        settings = with_defaults(data)
        case_sensitive = settings[KEY_CASE_SENSITIVE]
        return cls(
            channels=frozenset(settings[KEY_CHANNELS]),
            # D-08 scopes the case toggle to include and exclude; channel IDs always match case-insensitively
            channel_patterns=compile_patterns(settings[KEY_CHANNEL_REGEX]),
            include=compile_patterns(settings[KEY_INCLUDE], case_sensitive=case_sensitive),
            exclude=compile_patterns(settings[KEY_EXCLUDE], case_sensitive=case_sensitive),
            include_fields=frozenset(settings[KEY_INCLUDE_FIELDS]),
            exclude_fields=frozenset(settings[KEY_EXCLUDE_FIELDS]),
            min_duration=_duration(settings[KEY_MIN_DURATION]),
            max_duration=_duration(settings[KEY_MAX_DURATION]),
            window=TimeWindow.from_times(settings[KEY_TIME_FROM], settings[KEY_TIME_TO]),
            weekdays=frozenset(WEEKDAYS.index(name) for name in settings[KEY_WEEKDAYS]),
        )

    def _channel_selected(self, channel_id: str) -> bool:
        """Match selected IDs OR the channel regex on the ID; both empty selects every channel (D-02)."""
        if not self.channels and not self.channel_patterns:
            return True
        return channel_id in self.channels or any(pattern.search(channel_id) for pattern in self.channel_patterns)

    def _duration_matches(self, programme: Programme) -> bool:
        """
        Check stop - start against the inclusive bounds as exact timedeltas, no rounding (D-13).

        The parser's datetimes carry fixed offsets, so the difference is the real duration even across a DST change;
        never compute it on local-time conversions (Pitfall 6).
        """
        duration = programme.stop - programme.start
        if self.min_duration is not None and duration < self.min_duration:
            return False
        return self.max_duration is None or duration <= self.max_duration

    def _time_matches(self, programme: Programme, tz: tzinfo) -> bool:
        """Check the start time against the window and the weekdays in `tz`; the window's opening day is the weekday."""
        local = programme.start.astimezone(tz)
        day = self.window.anchor_date(local) if self.window is not None else local.date()
        return day is not None and (not self.weekdays or day.weekday() in self.weekdays)

    def _text_matches(self, programme: Programme) -> bool:
        if self.include and not _any_match(self.include, _field_values(programme, self.include_fields)):
            return False
        return not (self.exclude and _any_match(self.exclude, _field_values(programme, self.exclude_fields)))

    def apply(self, epg: EpgData, *, tz: tzinfo = UTC) -> FilterResult:
        """
        Return the matching programmes in feed order, each at most once, plus selected IDs the feed lacks (D-04).

        Window and weekdays are evaluated in `tz`, Home Assistant's time zone for the entity and the preview (D-10).
        Checks run cheapest first and every one must pass (D-14).
        """
        selected: dict[str, bool] = {}
        matches: list[Programme] = []
        bounded = self.min_duration is not None or self.max_duration is not None
        timed = self.window is not None or bool(self.weekdays)
        for programme in epg.programmes:
            channel_ok = selected.get(programme.channel_id)
            if channel_ok is None:
                channel_ok = selected[programme.channel_id] = self._channel_selected(programme.channel_id)
            if not channel_ok:
                continue
            if bounded and not self._duration_matches(programme):
                continue
            if timed and not self._time_matches(programme, tz):
                continue
            if self._text_matches(programme):
                matches.append(programme)
        missing = self.channels - epg.channels.keys() - selected.keys()
        return FilterResult(matches=tuple(matches), missing_channels=frozenset(missing))
